"""Independent acceptance: no imports from model/planners.
Rebuild geometry from original rectangles and check swept footprint against them.
Use a separate FIFO BFS as exact shortest-path oracle for unit-edge graph.
"""
from __future__ import annotations
from collections import deque
import math


def free_point(m,x,y):
    s=m['resolution_m']; rho=m['robot_halfwidth_m']+m['clearance_m']
    cx,cy=(x+.5)*s,(y+.5)*s
    if cx-rho<=1e-12 or cy-rho<=1e-12 or cx+rho>=m['width']*s-1e-12 or cy+rho>=m['height']*s-1e-12: return False
    for x0,y0,x1,y1 in m['obstacles']:
        if x0*s-rho-1e-12<=cx<=(x1+1)*s+rho+1e-12 and y0*s-rho-1e-12<=cy<=(y1+1)*s+rho+1e-12: return False
    return True


def geometry_free(m):
    return {(x,y) for y in range(m['height']) for x in range(m['width']) if free_point(m,x,y)}


def bfs_oracle(m,q,free=None):
    free=geometry_free(m) if free is None else free
    start,goal=tuple(q['start']),tuple(q['goal'])
    if start not in free or goal not in free: raise ValueError('invalid oracle endpoints')
    d={start:0}; queue=deque([start])
    while queue:
        u=queue.popleft()
        if u==goal: return d[u]
        x,y=u
        for v in ((x,y-1),(x-1,y),(x,y+1),(x+1,y)):
            if v in free and v not in d: d[v]=d[u]+1; queue.append(v)
    return None


def segment_clear(m,a,b):
    s=m['resolution_m']; rho=m['robot_halfwidth_m']+m['clearance_m']
    ax,ay=(a[0]+.5)*s,(a[1]+.5)*s; bx,by=(b[0]+.5)*s,(b[1]+.5)*s
    # For cardinal segment its swept square is exactly this axis-aligned rectangle.
    left,right=min(ax,bx)-rho,max(ax,bx)+rho
    bottom,top=min(ay,by)-rho,max(ay,by)+rho
    if left<=1e-12 or bottom<=1e-12 or right>=m['width']*s-1e-12 or top>=m['height']*s-1e-12:return False
    for x0,y0,x1,y1 in m['obstacles']:
        if left<=(x1+1)*s+1e-12 and right>=x0*s-1e-12 and bottom<=(y1+1)*s+1e-12 and top>=y0*s-1e-12:return False
    return True


def validate(m,q,out,oracle):
    errors=[]
    if not isinstance(out,dict): return {'valid':False,'errors':['not_object']}
    if out.get('status') not in ('ok','unreachable'):errors.append('status')
    path=out.get('path')
    if not isinstance(path,list): return {'valid':False,'errors':errors+['path_not_list']}
    if out.get('status')=='unreachable':
        if path: errors.append('unreachable_nonempty_path')
        if out.get('cost_steps') is not None or out.get('cost_m') is not None:errors.append('unreachable_cost')
        if oracle is not None:errors.append('false_unreachable')
        return {'valid':not errors,'errors':errors,'oracle_steps':oracle,'length_m':None,'heading_change_rad':None,'turn_count':None}
    if not path: return {'valid':False,'errors':errors+['empty_ok_path']}
    if any(not isinstance(p,list) or len(p)!=2 or any(type(x) is not int for x in p) for p in path):return {'valid':False,'errors':errors+['coordinate_type']}
    if path[0]!=q['start']:errors.append('wrong_start')
    if path[-1]!=q['goal']:errors.append('wrong_goal')
    for x,y in path:
        if not (0<=x<m['width'] and 0<=y<m['height']):errors.append('out_of_bounds');break
        if not free_point(m,x,y): errors.append('point_collision');break
    for a,b in zip(path,path[1:]):
        if abs(a[0]-b[0])+abs(a[1]-b[1])!=1:errors.append('non_adjacent');break
        if not segment_clear(m,a,b):errors.append('swept_collision');break
    steps=len(path)-1
    length=sum(math.hypot(b[0]-a[0],b[1]-a[1])*m['resolution_m'] for a,b in zip(path,path[1:]))
    if type(out.get('cost_steps')) is not int or out['cost_steps']!=steps:errors.append('step_cost')
    cost=out.get('cost_m')
    if type(cost) not in (int,float) or not math.isfinite(cost) or abs(cost-length)>1e-9:errors.append('meter_cost')
    if oracle is None: errors.append('false_reachable')
    elif steps!=oracle: errors.append('not_optimal')
    headings=[math.atan2(b[1]-a[1],b[0]-a[0]) for a,b in zip(path,path[1:])]
    turns=[abs((b-a+math.pi)%(2*math.pi)-math.pi) for a,b in zip(headings,headings[1:])]
    return {'valid':not errors,'errors':errors,'oracle_steps':oracle,'length_m':length,'heading_change_rad':sum(turns),'turn_count':sum(t>1e-12 for t in turns)}
