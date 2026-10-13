"""Independent continuous-coordinate replay. No OR-Tools or model matrices imported."""
import math,collections

def read_original(path):
    text=path.read_text();lines=text.splitlines();fleet=None;rows={}
    for pos,line in enumerate(lines):
        if line.strip()=='NUMBER     CAPACITY':fleet=tuple(map(int,lines[pos+1].split()))
        parts=line.split()
        if len(parts)==7:
            try:r=[int(x) for x in parts]
            except ValueError:continue
            assert r[0] not in rows
            rows[r[0]]=r[1:]
    if fleet is None:
        i=next(i for i,l in enumerate(lines) if l.strip()=='VEHICLE');fleet=tuple(map(int,lines[i+2].split()))
    assert sorted(rows)==list(range(101))
    return {'fleet':fleet[0],'capacity':fleet[1],'nodes':rows}

def check(d,routes,tol=1e-9):
    errors=[];visits=[];audits=[];total=0.0;min_margin=math.inf;nodes=d['nodes']
    if not isinstance(routes,list):return {'valid':False,'errors':['routes is not a list'],'distance':None}
    if len(routes)>d['fleet']:errors.append('vehicle limit exceeded')
    for idx,entry in enumerate(routes):
        r=entry['nodes'] if isinstance(entry,dict) else entry
        if not isinstance(r,list) or len(r)<3 or r[0]!=0 or r[-1]!=0 or 0 in r[1:-1]:
            errors.append(f'route{idx}: invalid depot/empty route structure');continue
        if any(type(j)!=int or j not in nodes for j in r):errors.append(f'route{idx}: unknown node');continue
        visits.extend(r[1:-1]);load=sum(nodes[j][2] for j in r[1:-1])
        if load>d['capacity']:errors.append(f'route{idx}: capacity exceeded')
        now=float(nodes[0][3]);dist=0.0;steps=[]
        for a,b in zip(r,r[1:]):
            x=nodes[a];y=nodes[b];leg=math.hypot(x[0]-y[0],x[1]-y[1]);dist+=leg
            arrival=now+x[5]+leg;service_start=max(arrival,float(y[3]));margin=float(y[4])-service_start
            if margin < -tol:errors.append(f'route{idx}: node{b} late by {-margin}')
            min_margin=min(min_margin,margin)
            steps.append({'node':b,'arrival':arrival,'service_start':service_start,'due':y[4],'margin':margin,'leg':leg})
            now=service_start
        total+=dist;audits.append({'nodes':r,'load':load,'distance':dist,'return_time':now,'steps':steps})
    counts=collections.Counter(visits);expected=set(nodes)-{0}
    missing=sorted(expected-set(counts));duplicates=sorted(x for x,v in counts.items() if v!=1)
    if missing:errors.append(f'missing customers:{missing}')
    if duplicates:errors.append(f'duplicate customers:{duplicates}')
    return {'valid':not errors,'errors':errors,'vehicles_used':len(routes),'served_unique':len(counts),'distance':total,'minimum_window_margin':min_margin if math.isfinite(min_margin) else None,'route_audits':audits}

def tests():
    # node record: x,y,demand,ready,due,service
    d={'fleet':2,'capacity':2,'nodes':{0:[0,0,0,0,20,0],1:[3,0,1,5,6,2],2:[4,0,1,8,9,1]}}
    assert check(d,[[0,1,2,0]])['valid']
    assert abs(check(d,[[0,1,2,0]])['distance']-8)<1e-12
    assert not check(d,[[0,1,0]])['valid']
    assert not check(d,[[0,1,2,1,0]])['valid']
    assert not check(d,[[0,2,1,0]])['valid']
    dc={**d,'capacity':1};assert not check(dc,[[0,1,2,0]])['valid']
    df={**d,'fleet':0};assert not check(df,[[0,1,2,0]])['valid']
    dr={**d,'nodes':{**d['nodes'],0:[0,0,0,0,10,0]}};assert not check(dr,[[0,1,2,0]])['valid']
    assert not check(d,[[0,0,1,2,0]])['valid']
    return ['valid_wait_service_distance','missing','duplicate','customer_late','capacity','fleet','depot_return','interior_depot']
