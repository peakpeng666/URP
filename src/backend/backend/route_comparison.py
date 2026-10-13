"""Read-only descriptive route comparison on a shared frozen continuous problem."""
from collections import Counter
from .routes import RouteReader
from .store import StoreError, canonical


def compare_routes(store, selections, instance=None):
    if not 1 <= len(selections) <= 8:
        raise StoreError('comparison_needs_items','请提供 1 到 8 个实验/版本。')
    readers=[RouteReader(store,item['experiment_id'],item.get('revision')) for item in selections]
    identities=[(reader.record['id'],reader.record['revision']) for reader in readers]
    if len(set(identities))!=len(identities):
        raise StoreError('duplicate_comparison_selection','同一实验/版本不能重复选择，否则会重复计算运行数。')
    contracts=[]
    for reader in readers:
        p=reader.record['provenance']
        contracts.append({'problem_spec_sha256':p['spec_sha256'],'input_file_sha256':p['input_sha256'],
                          'semantics':reader.index['semantics']})
    if any(c!=contracts[0] for c in contracts[1:]):
        raise StoreError('incomparable_route_problem','输入哈希、连续问题 spec 或距离/时间语义不同，不能混合比较。',409)
    if instance is not None and any(instance not in r.index['instances'] for r in readers):
        raise StoreError('not_found','比较实例不存在。',404)
    # A shared input is referenced once, regardless of the number of algorithms/budgets.
    input_refs={key:value['input_provenance']['instance_sha256'] for key,value in readers[0].index['instances'].items()
                if instance is None or key==instance}
    for reader in readers[1:]:
        for key,digest in input_refs.items():
            if key not in reader.index['instances'] or reader.index['instances'][key]['input_provenance']['instance_sha256']!=digest:
                raise StoreError('incomparable_route_problem','单实例内容哈希不一致。',409)
    rows=[];groups={}
    for reader in readers:
        for run in reader.index['runs'].values():
            if instance is not None and run['instance_id']!=instance:continue
            audit=run['checker']['audit']
            algorithm=run.get('algorithm',{'id':run['method'],'version':None})
            budget=run.get('budget',{'value':None,'unit':None,'scope':'not recorded as a comparable fixed search budget'})
            row={'experiment_id':reader.record['id'],'revision':reader.record['revision'],'run_id':run['run_id'],
                'instance_id':run['instance_id'],'algorithm':algorithm,'budget':budget,
                'source_status':run['source_status'],'solution_status':run['solution_status'],
                'full_service_success':run['full_service_success'],
                'route_distance':audit['total_distance'] if audit else None,
                'full_service_distance':audit['total_distance'] if audit and run['full_service_success'] else None,
                'research_protocol_sha256':run['provenance'].get('research_protocol_sha256',run['provenance']['spec_sha256']),
                'encoded_input_sha256':run['provenance'].get('encoded_input_sha256'),
                'run_sha256':run['provenance']['run_sha256']}
            rows.append(row)
            group_key=canonical([row['experiment_id'],row['revision'],algorithm,budget])
            group=groups.setdefault(group_key,{'experiment_id':row['experiment_id'],'revision':row['revision'],
                'algorithm':algorithm,'budget':budget,'run_count':0,'full_service_success_count':0,'solution_status_counts':Counter()})
            group['run_count']+=1;group['full_service_success_count']+=run['full_service_success'];group['solution_status_counts'][run['solution_status']]+=1
    best={}
    for row in rows:
        distance=row['full_service_distance']
        if distance is not None:best[row['instance_id']]=min(best.get(row['instance_id'],distance),distance)
    for row in rows:
        distance=row['full_service_distance'];row['distance_minus_best_returned_full']=None if distance is None else distance-best[row['instance_id']]
    budgets=[row['budget'] for row in rows]
    return {'schema_version':1,'comparison_mode':'descriptive_cross_algorithm_budget',
        'problem_spec_sha256':contracts[0]['problem_spec_sha256'],'input_file_sha256':contracts[0]['input_file_sha256'],
        'unique_input_count':len(input_refs),'input_references':input_refs,'semantics':contracts[0]['semantics'],
        'same_known_budget':bool(budgets) and all(b['value'] is not None and b==budgets[0] for b in budgets),
        'rows':rows,'row_count':len(rows),'groups':list(groups.values()),
        'interpretation':['距离差只对同一输入的已返回合法全服务路线计算；partial/no_solution/infeasible 不填0、不参与距离排名。',
            '不同算法/预算明确分组，这是描述性对照，不是相同计算预算下的公平性能或显著性结论。',
            '比较使用共同连续问题下的 checker 距离；整数编码约束、研究协议和来源哈希分别保留。',
            'best_returned_full 仅指本次选择中的最短已返回合法路线；不新增最优性证明。']}
