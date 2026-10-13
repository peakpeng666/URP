"""Splicing a reused KV span into a fresh forward pass, for the experiments in research log 20.

RoPE is a rotation, and rotations compose, so a cached key for a token that sat at absolute position
p is moved to p+d by rotating it by d. Verified over all 28 layers of Qwen2.5-7B on real cached keys:
max abs 7.0e-05, relative 2.2e-06 in fp32, against 1.6e+01 for the same reuse with no rotation. Values
carry no position and are untouched. Healing the whole reused span reproduces a plain forward to
1.6e-06, which is what makes the negative result in entry 20 a result rather than a bug.

Written against the transformers 4.55 `DynamicCache`, whose per-layer tensors live at
`cache.layers[i].keys` / `.values` (`key_cache` / `value_cache` are deprecated there).
"""
from __future__ import annotations

import sys
from typing import List, Sequence, Tuple

import torch
from transformers.cache_utils import DynamicCache

KV = List[Tuple[torch.Tensor, torch.Tensor]]


def kv_of(cache: DynamicCache) -> KV:
    """Per-layer (K, V) out of a cache."""
    return [(layer.keys, layer.values) for layer in cache.layers]


def cache_of(kv: KV) -> DynamicCache:
    """The inverse: a cache the model will accept as `past_key_values`."""
    cache = DynamicCache()
    for i, (k, v) in enumerate(kv):
        cache.update(k, v, i)
    return cache


def slice_kv(kv: KV, start: int, stop: int) -> KV:
    """The sequence positions [start, stop) of every layer."""
    return [(k[:, :, start:stop, :], v[:, :, start:stop, :]) for k, v in kv]


def concat_kv(first: KV, second: KV) -> KV:
    return [(torch.cat([a, c], 2), torch.cat([b, d], 2))
            for (a, b), (c, d) in zip(first, second)]


def rotate(kv: KV, delta: int, backbone, rotate_half) -> KV:
    """Move a reused span from wherever it was cached to `delta` positions later."""
    if delta == 0:
        return kv
    out: KV = []
    for k, v in kv:
        pos = torch.full((1, k.shape[2]), int(delta), device=k.device, dtype=torch.long)
        cos, sin = backbone.rotary_emb(k, pos)
        cos = cos.unsqueeze(1).to(k.dtype)          # [B, 1, T, D], broadcast over heads
        sin = sin.unsqueeze(1).to(k.dtype)
        out.append((k * cos + rotate_half(k) * sin, v))
    return out


def rotary_pieces(model):
    """The backbone and the `rotate_half` of whichever architecture this is."""
    backbone = getattr(model, model.base_model_prefix)
    return backbone, sys.modules[type(model).__module__].rotate_half


def forward(model, token_ids: Sequence[int], cache: DynamicCache, start: int):
    """Forward `token_ids` at absolute positions [start, start+n) against `cache`.

    `position_ids` is explicit because a spliced cache's length no longer tells the model where the
    new tokens are, and letting it default silently puts them at the wrong RoPE phase.
    """
    device = model.device
    ids = torch.as_tensor(list(token_ids), device=device, dtype=torch.long)[None]
    pos = torch.arange(start, start + ids.shape[1], device=device)[None]
    mask = torch.ones((1, start + ids.shape[1]), dtype=torch.long, device=device)
    with torch.no_grad():
        out = model(input_ids=ids, position_ids=pos, attention_mask=mask,
                    past_key_values=cache, use_cache=True)
    return out.logits[0, -1].float(), out.past_key_values


def label_probs(logits: torch.Tensor, label_ids: Sequence[int]):
    """The readout: softmax over the label tokens of the full-vocabulary log-softmax."""
    lp = torch.log_softmax(logits, -1)[torch.as_tensor(list(label_ids), device=logits.device)]
    return torch.softmax(lp, -1).cpu().numpy()


def common_affixes(a: Sequence[int], b: Sequence[int]) -> Tuple[int, int]:
    """(shared prefix length, shared suffix length) of two token sequences.

    The split between the fixed block and the state is discovered from two renderings rather than
    assumed from the prompt builder, so the experiment cannot disagree with what is really there.
    """
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    j = 0
    while j < min(len(a), len(b)) - i and a[-1 - j] == b[-1 - j]:
        j += 1
    return i, j


def ece(probs, labels, bins: int = 15) -> float:
    """Equal-mass expected calibration error, the definition bench/metrics.py uses."""
    import numpy as np

    conf, pred = probs.max(1), probs.argmax(1)
    correct = (pred == np.asarray(labels)).astype(float)
    order = np.argsort(conf)
    total = 0.0
    for chunk in np.array_split(order, bins):
        if len(chunk):
            total += len(chunk) / len(labels) * abs(correct[chunk].mean() - conf[chunk].mean())
    return float(total)
