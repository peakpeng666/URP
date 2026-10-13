"""Trusted handwritten baselines, not generated candidate programs."""
from __future__ import annotations
import heapq
from model import build_graph, check_query, neighbors


def plan(m,q,algorithm):
    """Includes input validation, graph building, search and path reconstruction.
    A*: Manhattan h in edge steps, admissible/consistent for this 4-neighbor graph.
    Dijkstra: h=0. Both optimize ONLY length, not heading changes.
    Heap key=(g+h,h,insertion_order,node,g); deterministic ties, no random seeds.
    """
    if algorithm not in ('astar','dijkstra'): raise ValueError('algorithm')
    free=build_graph(m); check_query(m,q,free)
    w,h=m['width'],m['height']; s=m['resolution_m']
    start=q['start'][1]*w+q['start'][0]; goal=q['goal'][1]*w+q['goal'][0]
    def heuristic(n):
        return abs(n%w-goal%w)+abs(n//w-goal//w) if algorithm=='astar' else 0
    inf=w*h+1; distance=[inf]*(w*h); parent=[-1]*(w*h)
    distance[start]=0; queue=[(heuristic(start),heuristic(start),0,start,0)]; serial=0
    work={'popped':0,'expanded':0,'stale_pops':0,'neighbor_checks':0,'relaxations':0,'heap_pushes':1,'max_frontier':1}
    found=False
    while queue:
        _,_,_,node,g=heapq.heappop(queue); work['popped']+=1
        if g!=distance[node]: work['stale_pops']+=1; continue
        work['expanded']+=1  # Non-stale settled vertex, includes the goal.
        if node==goal: found=True; break
        for nxt in neighbors(node,w,h,free):
            work['neighbor_checks']+=1
            tentative=g+1
            if tentative<distance[nxt]:
                distance[nxt]=tentative; parent[nxt]=node; serial+=1
                hv=heuristic(nxt); heapq.heappush(queue,(tentative+hv,hv,serial,nxt,tentative))
                work['relaxations']+=1; work['heap_pushes']+=1
        work['max_frontier']=max(work['max_frontier'],len(queue))
    path=[]
    if found:
        current=goal
        while current!=-1:
            path.append([current%w,current//w]); current=parent[current]
        path.reverse()
    return {'status':'ok' if found else 'unreachable','path':path,
            'cost_steps':distance[goal] if found else None,
            'cost_m':distance[goal]*s if found else None,'search':work}
