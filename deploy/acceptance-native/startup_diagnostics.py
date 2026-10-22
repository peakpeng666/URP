"""Private startup evidence -> bounded fixed-schema diagnostics only."""
import json,math,pathlib,re
PHASES={'starting','undocking','localizing','nav2_starting','ready','executing','stopping','stopped','failed'}
COUNTS=('clock','odom','scan','dock','ground_truth','amcl','global_map','local_map','cmd_vel','nav2_plan')
COMPONENTS=('session','sim','truth','localization','nav')
LABELS={'sensors_not_ready':'控制器/传感器未就绪','dock_not_ready':'初始充电座状态不可用','localization_timeout':'AMCL 初始定位超时','initialpose_unavailable':'initialpose 订阅者不可用','nav2_not_active':'Nav2 生命周期未激活','costmap_tf_not_ready':'代价地图/TF 未就绪','sim_launch_error':'官方仿真启动错误','assets_missing':'世界依赖缺失：','required_process_exit':'关键服务 ','required_node_exit':'的子节点意外退出：'}
CODES=set(LABELS)|{'launch_process_died','launch_server_failure','launch_uri_missing','segmentation_fault','python_module_missing','python_import_error'}
SID=re.compile(r'sim_[0-9]{8}T[0-9]{6}_[0-9a-f]{6}\Z')

def session_id(report):
    if not isinstance(report,dict):return None
    sid=report.get('session_id')
    if isinstance(sid,str) and SID.fullmatch(sid):return sid
    ids=[]
    for step in report.get('steps',[]) if isinstance(report.get('steps'),list) else []:
        if not isinstance(step,dict) or step.get('name')!='start simulation session' or step.get('ok') is not True:continue
        response=step.get('response');value=response.get('session_id') if isinstance(response,dict) else None
        if isinstance(value,str) and SID.fullmatch(value):ids.append(value)
    return ids[0] if len(set(ids))==1 else None

def num(value,integer=False,high=1e9):
    return value if type(value) in ((int,) if integer else (int,float)) and 0<=value<=high and math.isfinite(value) else None

def sanitize(raw):
    raw=raw if isinstance(raw,dict) else {};counts=raw.get('counts');counts=counts if isinstance(counts,dict) else {}
    stages=[]
    for row in raw.get('stages',[]) if isinstance(raw.get('stages'),list) else []:
        if isinstance(row,dict) and isinstance(row.get('phase'),str) and row['phase'] in PHASES and num(row.get('wall_s'),high=7200) is not None:stages.append({'phase':row['phase'],'wall_s':row['wall_s']})
    exits=[]
    for row in raw.get('component_exits',[]) if isinstance(raw.get('component_exits'),list) else []:
        if isinstance(row,dict) and row.get('component') in COMPONENTS and type(row.get('exit_code')) is int and -255<=row['exit_code']<=255:exits.append({'component':row['component'],'exit_code':row['exit_code']})
    codes=raw.get('error_codes');codes=codes if isinstance(codes,list) else []
    return {'report_available':raw.get('report_available') is True,'phase':raw.get('phase') if isinstance(raw.get('phase'),str) and raw['phase'] in PHASES else 'unknown','stages':stages[-20:],'counts':{k:num(counts.get(k),True) for k in COUNTS},'assets_complete':raw.get('assets_complete') if type(raw.get('assets_complete')) is bool else None,'assets_missing_count':num(raw.get('assets_missing_count'),True,100000),'error_codes':sorted({c for c in codes if isinstance(c,str) and c in CODES})[:16],'component_exits':exits[:20]}

def project(report,logs):
    report=report if isinstance(report,dict) else {};final=report.get('final_state') or {};final=final if isinstance(final,dict) else {}
    stages=[{'phase':r.get('name'),'wall_s':r.get('wall_s')} for r in (report.get('stages',[]) if isinstance(report.get('stages'),list) else []) if isinstance(r,dict)]
    assets=report.get('assets') or {};assets=assets if isinstance(assets,dict) else {}
    errors=report.get('errors',[]);errors=list(errors) if isinstance(errors,list) else []
    errors+=final.get('errors',[]) if isinstance(final.get('errors'),list) else []
    text='\n'.join(x[:65536] for x in errors[:20] if isinstance(x,str))
    codes=[code for code,label in LABELS.items() if label in text]
    exits=[]
    for component in COMPONENTS:
        text=logs.get(component,'')
        codes.extend(code for code,label in LABELS.items() if label in text)
        for marker,code in [('process has died','launch_process_died'),('CRITICAL FAILURE: SERVER','launch_server_failure'),('Unable to find uri','launch_uri_missing'),('Segmentation fault','segmentation_fault'),('ModuleNotFoundError:','python_module_missing'),('ImportError:','python_import_error')]:
            if marker in text:codes.append(code)
        for value in re.findall(r'\bexit code (-?\d{1,3})(?:\D|$)',text):exits.append({'component':component,'exit_code':int(value)})
    return sanitize({'report_available':bool(report),'phase':final.get('phase') or (stages[-1]['phase'] if stages else 'unknown'),'stages':stages,'counts':{k:report['counts'].get(k,0) for k in COUNTS} if isinstance(report.get('counts'),dict) else {},'assets_complete':assets.get('complete'),'assets_missing_count':len(assets['missing']) if isinstance(assets.get('missing'),list) else None,'error_codes':codes,'component_exits':exits})

def collect(runtime,sid):
    if not isinstance(sid,str) or not SID.fullmatch(sid):return sanitize({})
    root=pathlib.Path(runtime)/'sim'/sid
    if root.is_symlink() or root.parent.is_symlink():return sanitize({})
    def bounded(path,limit):
        if path.is_symlink() or path.parent.is_symlink() or not path.is_file():return b''
        with path.open('rb') as stream:
            stream.seek(0,2);size=stream.tell()
            if path.suffix=='.json' and size>limit:return b''
            stream.seek(max(0,size-limit));return stream.read(limit)
    try:report=json.loads(bounded(root/'session-report.json',2097152))
    except (ValueError,OSError):report={}
    logs={}
    for component in COMPONENTS:
        try:
            path=pathlib.Path(runtime)/'logs'/('sim-'+sid+'.log') if component=='session' else root/'logs'/(component+'.log')
            logs[component]=bounded(path,65536).decode('utf-8',errors='replace')
        except OSError:logs[component]=''
    return project(report,logs)
