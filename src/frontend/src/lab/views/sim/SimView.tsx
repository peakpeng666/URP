import { useMemo, useState } from 'react';
import type { Route } from '../../../app/router';
import { lab, exportUrl, fmt, useGatewayConnected, useLabResource } from '../../api';
import type { SimMode, XY } from '../../types';
import { Page } from '../../shell/Page';
import { Button, Card, Notice, Select, Switch, Metric } from '../../ui';
import { MapCanvas } from '../../canvas/MapCanvas';
import type { CanvasScene } from '../../canvas/types';
import { baseScene } from '../plan/planModel';
import { simPhaseLabel } from '../../shell/labels';
import s from '../Workbench.module.css';

export function SimView({ route }: { route: Route }) {
  const connected=useGatewayConnected();const rid=route.params.get('run');
  const runs=useLabResource('runs',()=>lab.runs({limit:60}));
  const solution=useLabResource('sol-'+rid,()=>rid?lab.run(rid):Promise.resolve(null));
  const session=useLabResource('sim',()=>lab.simState(),{event:'sim_state',pollMs:2000});
  const history=useLabResource('sim-history',()=>lab.simRuns(),{pollMs:3000});
  const [mode,setMode]=useState<SimMode>('follow_path');const [gui,setGui]=useState(false);const [rviz,setRviz]=useState(false);
  const [error,setError]=useState<string|null>(null);const [busy,setBusy]=useState(false);
  const [localization,setLocalization]=useState<'ground_truth'|'amcl'>('amcl');
  const [historyId,setHistoryId]=useState('');
  const st=session.data;const sol=solution.data;const sc=sol?.scenario_snapshot;
  const latest=historyId?history.data?.sim_runs.find(r=>r.sim_run_id===historyId&&r.run_id===rid):(st?.execution?.run_id===rid?st.execution:history.data?.sim_runs.find(r=>r.run_id===rid));
  const scene=useMemo<CanvasScene|null>(()=>{
    if(!sc||!sol)return null;const out=baseScene(sc,sol.instance??sc.instance);
    out.paths=sol.routes.map((r,i)=>({id:'plan'+i,points:r.polyline,color:'#007aff',width:3,chevrons:true}));
    if(latest){out.paths.push({id:'truth',points:latest.actual.ground_truth.map(p=>[p[1],p[2]] as XY),color:'#28a745',width:3,layer:'trails'});out.paths.push({id:'amcl',points:latest.actual.amcl.map(p=>[p[1],p[2]] as XY),color:'#9a45c9',width:2,dash:[4,4],layer:'trails'});out.nodes=out.nodes?.map(n=>{const t=latest.tasks.find(t=>Math.hypot(t.xy[0]-n.xy[0],t.xy[1]-n.xy[1])<.001);return t?{...n,state:t.state}:n;});}
    if(st?.world===sc.sim.world&&st.robot?.ground_truth){const p=st.robot.ground_truth;out.robots=[{id:'robot',xy:[p[0],p[1]],yaw:p[2],color:'#28a745',radius:.175,title:'Gazebo 真值'}];}
    return out;
  },[sc,sol,latest,st]);
  async function act(fn:()=>Promise<unknown>){setBusy(true);setError(null);try{await fn();session.reload();history.reload();}catch(e){setError(String(e));}finally{setBusy(false);}}
  const active=st&&!['stopped','failed'].includes(st.phase);
  return <Page title="机器人仿真" subtitle="蓝：规划路径 · 绿：实际轨迹 · 紫：定位估计" actions={<a href="#/plan">返回规划</a>}>
    {!connected&&<Notice tone="error">与工作台服务的连接已断开</Notice>}
    {(error||session.error||solution.error)&&<Notice tone="error">{error||session.error?.message||solution.error?.message}</Notice>}
    <div className={s.workspace}><aside className={s.stack}>
      <Card title="仿真会话"><div className={s.pad}>
        <label className={s.field}>待执行规划<Select aria-label="待执行规划" value={rid??''} onChange={e=>{location.hash=`#/sim?run=${e.target.value}`;}}><option value="">选择规划结果</option>{runs.data?.runs.filter(r=>r.frame.kind==='map'&&r.state==='done').map(r=><option key={r.run_id} value={r.run_id}>{r.scenario_id} · {r.run_id}</option>)}</Select></label>
        <strong>{st?simPhaseLabel(st.phase):'读取状态中'}</strong><p>{st?.world??sc?.sim.world??'尚未选择世界'} · {st?.session_id??'无会话'}</p>
        <label className={s.field}>定位方式<Select aria-label="定位方式" value={active?st?.localization??'amcl':localization} disabled={!!active} onChange={e=>setLocalization(e.target.value as 'ground_truth'|'amcl')}><option value="ground_truth">真值定位</option><option value="amcl">AMCL 激光定位</option></Select></label>
        <Notice>{(active?st?.localization:localization)==='ground_truth'?'用仿真真值定位，排除定位误差，专注比较规划与跟踪。':'用 AMCL 激光定位闭环行驶，更接近真实机器人。'}</Notice>
        <Switch label="显示 Gazebo 窗口" checked={gui} onChange={setGui} disabled={!!active}/><Switch label="显示 RViz 窗口" checked={rviz} onChange={setRviz} disabled={!!active}/>
        <div className={s.row}><Button variant="primary" disabled={busy||!connected||!sc||!!active} onClick={()=>void act(()=>lab.simStart({world:sc!.sim.world!,spawn:sc!.sim.spawn??undefined,gui,rviz,localization}))}>启动仿真</Button><Button variant="destructive" disabled={busy||!connected||!active} onClick={()=>void act(()=>lab.simStop())}>关闭仿真</Button></div>
        {st?.phase==='ready'&&<div className={s.row}><Button onClick={()=>void act(()=>lab.simGui(st.components.gui!=='running'))}>Gazebo 窗口</Button><Button onClick={()=>void act(()=>lab.simRviz(st.components.rviz!=='running'))}>RViz 窗口</Button></div>}
        {st?.errors.map((e,i)=><Notice tone="error" key={i}>{e}</Notice>)}
        <details><summary>启动阶段与传感器</summary><pre>{JSON.stringify({stages:st?.stages,telemetry:st?.telemetry,components:st?.components},null,2)}</pre></details>
      </div></Card>
      <Card title="执行方式"><div className={s.pad}>
        <Select aria-label="执行方式" value={mode} onChange={e=>setMode(e.target.value as SimMode)}><option value="follow_path">沿规划路径行驶</option><option value="nav2_waypoints" disabled={sc?.problem_class==='coverage'}>按任务顺序逐点导航（Nav2）</option></Select>
        <p>{mode==='follow_path'?'机器人沿规划出的路径行驶，Nav2 只负责跟踪控制。':'按规划的任务顺序，由 Nav2 自行规划每一段路径。'}</p>
        <Button variant="primary" disabled={busy||!connected||!rid||st?.phase!=='ready'||!sol?.check?.valid||mode==='follow_path'&&!sol?.map_check?.collision_free} onClick={()=>{setHistoryId('');void act(()=>lab.simExecute(rid!,mode));}}>执行所选路线</Button>
        {latest&&!['succeeded','failed','canceled'].includes(latest.state)&&<Button variant="destructive" disabled={busy||!connected} onClick={()=>void act(()=>lab.simCancel(latest.sim_run_id))}>取消执行</Button>}
        <details><summary>已知问题</summary>{st?.known_issues.map((k,i)=><p key={i}>{k}</p>)}</details>
      </div></Card>
    </aside><div className={s.stack}>
      <div className={s.canvas}>{scene?<MapCanvas scene={scene} fitKey={rid??''} ariaLabel="仿真规划与实际轨迹"/>:<div className={s.pad}>选择一个地图场景的规划结果。</div>}</div>
      <Card title="实际执行结果"><div className={s.pad}>{latest?<>
        <label className={s.field}>执行记录<Select aria-label="执行记录" value={historyId} onChange={e=>setHistoryId(e.target.value)}><option value="">当前 / 最近一次执行</option>{history.data?.sim_runs.filter(r=>r.run_id===rid).map(r=><option key={r.sim_run_id} value={r.sim_run_id}>{fmt.time(r.created_utc)} · {r.mode} · {r.state}</option>)}</Select></label>
        <div className={s.row}><strong data-testid="sim-result">{({succeeded:'执行成功',failed:'执行失败',canceled:'已取消',queued:'排队中',approach:'前往起点',executing:'执行中'})[latest.state]}</strong><span className={s.meta}>{latest.sim_run_id}</span></div>
        <p>{latest.mode==='follow_path'?'沿规划路径行驶':'逐点导航'} · {latest.localization==='ground_truth'?'真值定位':'AMCL 定位'} · 统计不含前往起点的一段</p>
        {latest.progress&&<p>路径段 {latest.progress.leg} / {latest.progress.legs_total}</p>}
        {sc?.problem_class==='coverage'&&<Notice>作业区实际覆盖 {latest.metrics.actual_working_coverage_fraction==null?'—':fmt.num(latest.metrics.actual_working_coverage_fraction*100)+'%'} · 全田块 {latest.metrics.actual_field_coverage_fraction==null?'—':fmt.num(latest.metrics.actual_field_coverage_fraction*100)+'%'}</Notice>}
        {latest.metrics.actual_map_check&&<Notice tone={latest.metrics.actual_map_check.collision_free?'ok':'error'}>实际轨迹{latest.metrics.actual_map_check.collision_free?'未碰撞':'有碰撞风险'} · 最小净空 {fmt.num(latest.metrics.actual_map_check.min_clearance_m,3)} m</Notice>}
        {latest.error&&<Notice tone="error">{latest.error}</Notice>}
        <div className={s.metrics}>{sc?.problem_class==='coverage'?<Metric label="实际作业区覆盖" value={latest.metrics.actual_working_coverage_fraction==null?'—':fmt.num(latest.metrics.actual_working_coverage_fraction*100)} unit="%"/>:<Metric label="按序到达" value={`${latest.metrics.tasks_reached??0} / ${latest.metrics.tasks_total??0}`}/>}<Metric label="实际长度" value={fmt.num(latest.metrics.actual_length_m)} unit="m"/><Metric label={latest.mode==='follow_path'?'最大跟踪偏差':'偏离规划路径'} value={fmt.num(latest.metrics.cross_track_max_m,3)} unit="m"/><Metric label="最终位置误差" value={fmt.num(latest.metrics.final_error_m,3)} unit="m"/></div>
        <p>真值 {latest.actual.ground_truth.length} 点 · 定位 {latest.actual.amcl.length} 点</p>
        <div className={s.row}><a href={exportUrl.simRun(latest.sim_run_id,'json')} download>导出实验 JSON</a><a href={exportUrl.simRun(latest.sim_run_id,'csv')} download>导出轨迹 CSV</a><a href={exportUrl.run(latest.run_id,'json')} download>导出对应规划</a></div>
        <details><summary>任务、动作状态与原始结果</summary><pre>{JSON.stringify(latest,null,2)}</pre></details>
      </>:<p>启动仿真，就绪后执行路线。</p>}</div></Card>
    </div></div>
  </Page>;
}
