"""Pure Python, integer-cell orchard graph contract. Coordinates are [x, y]."""
from __future__ import annotations
import math


def check_map(m):
    if not isinstance(m, dict): raise ValueError('map must be object')
    for key in ('width', 'height'):
        if type(m.get(key)) is not int or m[key] < 1: raise ValueError(key)
    for key in ('resolution_m', 'robot_halfwidth_m', 'clearance_m'):
        v = m.get(key)
        if type(v) not in (int,float) or not math.isfinite(v) or v < 0: raise ValueError(key)
    if m['resolution_m'] <= 0: raise ValueError('resolution')
    for r in m['obstacles']:
        if len(r) != 4 or any(type(v) is not int for v in r): raise ValueError('rectangle')
        x0,y0,x1,y1=r
        if not (0<=x0<=x1<m['width'] and 0<=y0<=y1<m['height']): raise ValueError('rectangle bounds')


def build_graph(m):
    """Dilate raw closed obstacle-cell rectangles for square footprint + clearance.
    Exact integer-center exclusion radius floor(rho / resolution + 0.5).
    Touching any obstacle or exterior counts as collision.
    """
    check_map(m)
    w,h=m['width'],m['height']; s=m['resolution_m']
    rho=m['robot_halfwidth_m']+m['clearance_m']
    cells=bytearray([1])*(w*h)
    for y in range(h):
        for x in range(w):
            if min((x+.5)*s,(y+.5)*s,(w-x-.5)*s,(h-y-.5)*s)<=rho+1e-12:
                cells[y*w+x]=0
    inflation=math.floor(rho/s+.5+1e-12)
    for x0,y0,x1,y1 in m['obstacles']:
        for y in range(max(0,y0-inflation),min(h,y1+inflation+1)):
            for x in range(max(0,x0-inflation),min(w,x1+inflation+1)):
                cells[y*w+x]=0
    return cells


def check_query(m,q,free):
    for key in ('start','goal'):
        p=q.get(key)
        if not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(v) is not int for v in p): raise ValueError(key)
        x,y=p
        if not (0<=x<m['width'] and 0<=y<m['height']) or not free[y*m['width']+x]: raise ValueError(key+' blocked/outside')


def neighbors(node,w,h,free):
    """Fixed E,N,W,S ordering. No diagonal edges or corner-cutting."""
    x,y=node%w,node//w
    if x+1<w and free[node+1]: yield node+1
    if y+1<h and free[node+w]: yield node+w
    if x>0 and free[node-1]: yield node-1
    if y>0 and free[node-w]: yield node-w
