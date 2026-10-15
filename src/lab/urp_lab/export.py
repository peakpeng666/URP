"""Portable, self-contained records. Local map geometry is not Earth longitude/latitude."""
import csv
import io
import json

def pack(record, fmt, stem):
    if fmt == 'json': return json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False).encode(), 'application/json', stem+'.json'
    raise ValueError('不支持的导出格式')

def rows_csv(rows, fields, stem):
    stream = io.StringIO(); w=csv.DictWriter(stream,fieldnames=fields); w.writeheader(); w.writerows(rows)
    return stream.getvalue().encode('utf-8-sig'),'text/csv',stem+'.csv'

def export_run(sol, fmt):
    stem=sol['run_id']
    if fmt=='json': return pack(sol,fmt,stem)
    if fmt=='csv':
        rows=[dict(run_id=stem,vehicle=r['vehicle'],point=i,x=p[0],y=p[1],units=sol['frame']['units'],instance_sha256=sol['instance_sha256']) for r in sol['routes'] for i,p in enumerate(r['polyline'])]
        return rows_csv(rows,['run_id','vehicle','point','x','y','units','instance_sha256'],stem)
    if fmt=='geojson':
        # Explicit local-coordinate extension, never advertise WGS84 / RFC7946 geographic compatibility.
        obj={'type':'FeatureCollection','coordinate_reference':sol['frame'], 'warning':'Local coordinates; NOT WGS84 / RFC7946 geographic coordinates',
             'features':[{'type':'Feature','properties':{'run_id':stem,'vehicle':r['vehicle']},'geometry':{'type':'LineString','coordinates':r['polyline']}} for r in sol['routes'] if len(r['polyline'])>=2]}
        return json.dumps(obj,ensure_ascii=False).encode(),'application/json',stem+'.geojson'
    raise ValueError('格式须为 json/csv/geojson')

def export_sim_run(run, fmt):
    if fmt=='json': return pack(run,fmt,run['sim_run_id'])
    if fmt=='csv':
        rows=[dict(sim_run_id=run['sim_run_id'],source=k,t_sim=p[0],x_m=p[1],y_m=p[2],yaw_rad=p[3]) for k,pts in run['actual'].items() for p in pts]
        return rows_csv(rows,['sim_run_id','source','t_sim','x_m','y_m','yaw_rad'],run['sim_run_id'])
    raise ValueError('格式须为 json/csv')

def export_compare(solutions, fmt):
    if fmt=='json': return pack(solutions,fmt,'urp-compare')
    if fmt=='csv':
        rows=[dict(run_id=s['run_id'],scenario=s['scenario_id'],instance_sha256=s['instance_sha256'],algorithm=s['algorithm']['id'],state=s['state'],status=s['status'],cost=s['objective']['value'],unit=s['objective']['unit'],valid=(s.get('check')or{}).get('valid')) for s in solutions]
        return rows_csv(rows,['run_id','scenario','instance_sha256','algorithm','state','status','cost','unit','valid'],'urp-compare')
    raise ValueError('格式须为 json/csv')
