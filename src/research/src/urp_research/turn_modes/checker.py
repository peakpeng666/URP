"""Independent witness checker: reads raw graph and route witnesses only.
Never imports solver tables, modes or precomputed shortest-path distances.
"""
from collections import Counter

def check(instance,solution):
    errors=[]; total=0; all_service=[]; details=[]
    depot=instance['depot'];cap=instance['capacity']
    arcs={(u,v):cost for u,v,cost in instance['arcs']}
    forbidden={tuple(t) for t in instance['forbidden_turns']}
    penalties={(u,v,w):c for u,v,w,c in instance['turn_penalties']}
    tasks={t['id']:t for t in instance['customers']}
    if solution.get('status')!='optimal':
        return {'valid':False,'errors':['no_feasible_witness'],'computed_cost':None,'routes':[]}
    for ri,r in enumerate(solution.get('routes',[])):
        nodes=r.get('nodes',[]);services=r.get('services',[]);cost=0;violations=[];load=0
        if len(nodes)<2 or nodes[0]!=depot or nodes[-1]!=depot: errors.append(f'route{ri}:depot_endpoints')
        for j,(u,v) in enumerate(zip(nodes,nodes[1:])):
            if (u,v) not in arcs: errors.append(f'route{ri}:unknown_arc:{j}')
            else:cost+=arcs[u,v]
        for j,triple in enumerate(zip(nodes,nodes[1:],nodes[2:])):
            if triple in forbidden:
                errors.append(f'route{ri}:forbidden_turn:{j+1}');violations.append({'position':j+1,'triple':list(triple)})
            cost+=penalties.get(triple,0)
        lastpos=-1
        for s in services:
            cid=s.get('customer');p=s.get('position');all_service.append(cid)
            if cid not in tasks:errors.append(f'route{ri}:unknown_customer');continue
            if type(p) is not int or not 0<=p<len(nodes) or nodes[p]!=tasks[cid]['node']:errors.append(f'route{ri}:service_location')
            if type(p) is int:
                if p<lastpos:errors.append(f'route{ri}:service_order')
                lastpos=p
            load+=tasks[cid]['demand']
        if not services:errors.append(f'route{ri}:empty_service_route')
        if load>cap:errors.append(f'route{ri}:capacity')
        if r.get('cost')!=cost:errors.append(f'route{ri}:cost_mismatch')
        total+=cost;details.append({'route':ri,'load':load,'cost':cost,'forbidden_turns':violations})
    counts=Counter(all_service)
    if counts!=Counter({k:1 for k in tasks}):errors.append('exact_once_service')
    if solution.get('cost')!=total:errors.append('total_cost_mismatch')
    return {'valid':not errors,'errors':errors,'computed_cost':total,'routes':details}
