"""Independent checker. Does not import solver functions or cached matrix."""
from math import sqrt
from collections import Counter

def audit(instance, routes):
    nodes={n['id']:n for n in instance['nodes']}
    expected=set(nodes)-{0}
    seen=[j for route in routes for j in route]
    counts=Counter(seen)
    duplicates=sorted(j for j,c in counts.items() if c>1)
    unknown=sorted(set(seen)-expected)
    missing=sorted(expected-set(seen))
    violations=[]
    if len(routes)!=instance['vehicles']: violations.append('vehicle_count')
    if duplicates: violations.append('duplicate')
    if unknown: violations.append('unknown')
    schedules=[]; total=0.; late_count=0; total_late=0.; overload_count=0; depot_late_count=0
    for vi,route in enumerate(routes):
        load=sum(nodes[j]['demand'] for j in route if j in expected)
        overload=max(0,load-instance['capacity'])
        if overload: overload_count+=1; violations.append('overload')
        now=instance['depart_time']; previous=0; distance=0.; stops=[]
        for j in route:
            if j not in expected: continue
            n=nodes[j]; p=nodes[previous]
            leg=sqrt((n['x']-p['x'])**2+(n['y']-p['y'])**2)
            arrival=now+leg; start=max(arrival,n['window'][0]); wait=start-arrival
            late=max(0.,start-n['window'][1]); departure=start+n['service']
            if late>1e-9: late_count+=1; total_late+=late; violations.append('late_start')
            distance+=leg
            stops.append({'node':j,'arrival':arrival,'wait':wait,'start':start,'depart':departure,'window_open':n['window'][0],'window_close':n['window'][1],'lateness':late,'demand':n['demand'],'leg_distance':leg})
            previous=j;now=departure
        last=nodes[previous]; depot=nodes[0]
        return_leg=sqrt((last['x']-depot['x'])**2+(last['y']-depot['y'])**2)
        distance+=return_leg; return_time=now+return_leg
        depot_lateness=max(0.,return_time-instance['return_deadline'])
        if depot_lateness>1e-9: depot_late_count+=1;violations.append('depot_late')
        total+=distance
        schedules.append({'vehicle':vi,'route':route,'load':load,'overload':overload,'distance':distance,'stops':stops,'return_leg_distance':return_leg,'return_time':return_time,'depot_lateness':depot_lateness})
    feasible=not violations
    return {'route_feasible':feasible,'full_service_feasible':feasible and not missing,'served_unique':len(set(seen)&expected),'missing':missing,'duplicates':duplicates,'unknown':unknown,'violations':violations,'late_starts':late_count,'total_lateness':total_late,'overloaded_vehicles':overload_count,'late_depot_returns':depot_late_count,'total_distance':total,'schedules':schedules}

def tests():
    i={'nodes':[{'id':0,'x':0.,'y':0.,'demand':0,'service':0,'window':[0,20]},{'id':1,'x':3.,'y':4.,'demand':2,'service':2.,'window':[7.,7.]},{'id':2,'x':0.,'y':6.,'demand':2,'service':1.,'window':[0.,20.]}], 'vehicles':2,'capacity':3,'depart_time':0,'return_deadline':20}
    out=[]
    a=audit(i,[[1],[2]])
    assert a['full_service_feasible'] and a['total_distance']==22
    s=a['schedules'][0]['stops'][0]
    assert (s['arrival'],s['wait'],s['start'],s['depart'])==(5.,2.,7.,9.)
    assert a['schedules'][0]['return_time']==14.
    out.append('exact_boundary_wait_and_return')
    a=audit(i,[[1,2],[]]);assert a['overloaded_vehicles']==1;out.append('overload')
    a=audit(i,[[2,1],[]]);assert a['late_starts']==1;out.append('late_start_not_arrival')
    a=audit(i,[[1],[1]]);assert a['duplicates']==[1] and a['missing']==[2] and not a['route_feasible'];out.append('duplicate_and_missing')
    a=audit(i,[[1],[99]]);assert a['unknown']==[99];out.append('unknown_node')
    j=dict(i,return_deadline=13);assert audit(j,[[1],[2]])['late_depot_returns']==1;out.append('late_depot')
    a=audit(i,[[],[]]);assert a['route_feasible'] and not a['full_service_feasible'] and a['missing']==[1,2];out.append('empty_is_not_full')
    assert not audit(i,[[1,2]])['route_feasible'];out.append('vehicle_count')
    return out
