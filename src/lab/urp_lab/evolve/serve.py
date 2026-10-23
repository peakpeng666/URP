"""Serve a promoted coverage try-order model to the recommender, with fingerprint and scope gates.

The model document (``src/lab/models/coverage-order-v1.json``) is produced by ``policy.export_model`` from
development fields only. Here it is used only when (1) its artifact hash matches, (2) the instance's machine
parameters match one of the evaluated profiles, and (3) the instance's scaled feature vector lies within the
training cloud (nearest-neighbour distance ≤ the 99th percentile of leave-one-field-out distances). Otherwise
the recommender keeps its rules. The result never claims a sealed-test evaluation.
"""
from __future__ import annotations

import hashlib
import json
import math
from functools import lru_cache

import numpy as np

from .. import paths
from . import features as F

MODEL = paths.LAB / 'models' / 'coverage-order-v1.json'
SELECTOR_ID = 'lab.coverage.order.v1'
MACHINE_KEYS = ('swath_width', 'turn_radius', 'headland_width')


@lru_cache(maxsize=4)
def _load(mtime: float):
    doc = json.loads(MODEL.read_text(encoding='utf-8'))
    payload = json.dumps(doc['artifact'], sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(payload).hexdigest() != doc['artifact_sha256']:
        raise ValueError('模型指纹不匹配')
    return doc


def _profile(inst: dict, profiles: dict) -> str | None:
    for name, spec in profiles.items():
        if all(math.isclose(float(inst.get(k, -1)), float(spec[k]), rel_tol=1e-6) for k in MACHINE_KEYS):
            return name
    return None


def _scores(art: dict, z: np.ndarray) -> np.ndarray:
    """Expected penalised ratio per configuration (lower is better)."""
    P = art['penalty']
    if art['kind'] == 'logit':
        probs = []
        for m in art['logit']:
            if 'const' in m:
                probs.append(m['const'])
            else:
                w = np.array(m['w'])
                probs.append(1 / (1 + math.exp(-(w[0] + z @ w[1:]))))
        probs = np.array(probs)
        return probs * np.array(art['mu']) + (1 - probs) * P
    Z, R = np.array(art['train_Z']), np.array(art['train_rho'])
    d = np.sqrt(((Z - z) ** 2).sum(axis=1))
    idx = np.argsort(d, kind='stable')[: art['k']]
    w = 1.0 / (d[idx] + 1e-9)
    return (R[idx] * w[:, None]).sum(axis=0) / w.sum()


def recommend(scenario: dict, instance: dict) -> dict:
    base = {'id': SELECTOR_ID, 'status': 'unavailable', 'prediction': None, 'required': [str(MODEL)],
            'scope': '开发侧（荷兰田块）分组交叉验证评估的覆盖配置尝试顺序；爱沙尼亚/立陶宛封存测试尚未运行，不作为正式结论'}
    if scenario.get('problem_class') != 'coverage':
        return dict(base, status='not_applicable', reason=None, required=[])
    if not MODEL.is_file():
        return dict(base, reason='覆盖尝试顺序模型尚未导出；当前使用规则')
    try:
        doc = _load(MODEL.stat().st_mtime)
        art = doc['artifact']
        base = dict(base, required=[], model_sha256=doc['artifact_sha256'], cv_evaluation=doc.get('evaluation'))
        if art['feature_version'] != F.VERSION:
            return dict(base, status='out_of_scope', reason=f"模型特征版本 {art['feature_version']} 与当前 {F.VERSION} 不一致；当前使用规则")
        prof = _profile(instance, art['profiles'])
        if prof is None:
            return dict(base, status='out_of_scope', reason='幅宽/转弯半径/地头宽度不属于已评估的三种机具配置；当前使用规则')
        feats = F.coverage_features(instance['field'], instance.get('obstacles') or [], instance['swath_width'],
                                    instance['turn_radius'], instance['headland_width'])
        x = np.array([feats[k] for k in art['features']], dtype=float)
        for j, k in enumerate(art['features']):
            if k in art['log_features']:
                x[j] = math.log1p(max(x[j], 0.0))
        z = (x - np.array(art['scaler']['mu'])) / np.array(art['scaler']['sd'])
        Z = np.array(art.get('train_Z') or [])
        nn = float(np.sqrt(((Z - z) ** 2).sum(axis=1)).min()) if len(Z) else None
        if nn is None or nn > art['scope']['nn_distance_q99']:
            return dict(base, status='out_of_scope', reason=f'田块特征离训练样本过远（最近距离 {nn:.2f} > {art["scope"]["nn_distance_q99"]:.2f}）；当前使用规则')
        lo, hi = np.array(art['scope']['feature_min']), np.array(art['scope']['feature_max'])
        outside = [art['features'][j] for j in range(len(x)) if x[j] < lo[j] - 1e-9 or x[j] > hi[j] + 1e-9]
        if len(outside) > 2:
            return dict(base, status='out_of_scope', reason='多个田块特征超出训练范围：' + '、'.join(outside[:4]) + '；当前使用规则')
        scores = _scores(art, z)
        rank = {j: t for t, j in enumerate(art['static_order'])}
        order = sorted(range(len(art['configs'])), key=lambda j: (scores[j], rank[j]))
        steps = []
        for j in order:
            name = art['configs'][j]
            alg, params = art['config_params'][name]
            steps.append({'config': name, 'algorithm_id': alg, 'params': params, 'expected_ratio': float(scores[j])})
        return dict(base, status='available', reason='开发侧分组交叉验证（留出田块）评估的实验策略；封存测试未运行。先按顺序尝试，独立验算失败再试下一项。',
                    prediction={'order': steps, 'profile': prof, 'nearest_distance': nn, 'features': feats},
                    features_outside_range=outside)
    except Exception as exc:  # noqa: BLE001 - a broken model must never break the recommender
        return dict(base, status='unavailable', reason='覆盖尝试顺序模型不可用：' + str(exc)[:200])
