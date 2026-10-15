"""Rules and a narrow learned prototype, with explicit provenance and out-of-scope fallback."""
from .solvers import catalog
from . import paths
from . import learned

def recommend(scenario, instance):
    pc = scenario['problem_class']
    n = len(instance.get('customers', [])) if pc == 'turn_routing' else max(0, len(instance.get('demands', []))-1)
    preferred = 'urp.turn_mode_dp' if pc == 'turn_routing' and n <= 12 else 'ortools.gls+urp.layered' if pc == 'turn_routing' else 'pyvrp.hgs' if pc == 'euclidean_cvrp' else 'panel.boustrophedon'
    if pc=='coverage' and next(a for a in catalog() if a['id']=='f2c.boustrophedon')['available']:
        preferred='f2c.boustrophedon'
    model=learned.recommend(scenario,instance)
    use_model=bool(model and model['status']=='available')
    if use_model:preferred=model['prediction']['selected']
    rows = []
    for a in sorted((a for a in catalog() if pc in a['problem_classes']), key=lambda a:a['id'] != preferred):
        ok = a['available'] and n <= a['limits'].get('max_tasks', 10000)
        rows.append(dict(algorithm_id=a['id'], rank=len(rows)+1, applicable=ok, suitability='推荐' if a['id']==preferred and ok else '可用' if ok else '不适用',
                         reasons=[a['description'] if ok else a['unavailable_reason'] or f'任务数 {n} 超过精确算法限制'],
                         suggested_params={p['name']:p['default'] for p in a['params']}))
    if use_model:
        for r in rows:r['suggested_params'].update(time_limit_s=learned.BUDGET,seed=11)
    return dict(problem_class=pc, policy='knn-crc-local-v1' if use_model else 'rules-v1', features=[dict(name='任务数',key='n_tasks',value=n,unit=None)],
                learned_selector=model or dict(id='urp.cvrp_selection.knn_crc',status='unavailable' if pc=='euclidean_cvrp' else 'not_applicable',
                    reason='此任务类型未部署学习推荐，采用规则；历史研究训练数据仍未恢复',required=[str(paths.CVRP_SELECTION_DATA/'data/raw.jsonl')],prediction=None),
                ranking=rows,recommended=preferred,explanation=('已训练的 kNN 成本预测 + 校准风险门控；未接受替代时回退训练集最佳固定算法。建议预算 0.25 s，改变预算后模型比较不再适用。' if use_model else '按问题类型、任务规模、算法可用性选择；不代表实测性能最优。'))
