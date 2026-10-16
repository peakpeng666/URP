import { useState } from 'react';
import type { Instance, Scenario } from '../../types';
import { Button, Input, Select } from '../../ui';
import { asCoverage, asCvrp, asTurn, addCvrpPoint, removeCvrpPoint, setCapacity, setDemand, taskRows, toggleTurnTask } from './planModel';
import s from '../Workbench.module.css';

export function TaskEditor({scenario,instance,onChange}:{scenario:Scenario;instance:Instance;onChange:(i:Instance)=>void}) {
  const [node,setNode]=useState('');const [x,setX]=useState(0);const [y,setY]=useState(0);
  const pc=scenario.problem_class;
  if(pc==='coverage'){
    const v=asCoverage(instance);
    const fields=[['headland_width','地头宽度 (m)',.1],['swath_width','作业幅宽 (m)',.05],['turn_radius','最小转弯半径 (m)',.05],['robot_width','机器人宽度 (m)',.01],['angle_deg','作业行角度 (°)',1]] as const;
    return <div className={s.formGrid}>{fields.map(([k,label,step])=><label className={s.field} key={k}>{label}<Input aria-label={label} type="number" step={step} min={k==='angle_deg'?0:.01} value={v[k]??0} onChange={e=>onChange({...v,[k]:Number(e.target.value)})}/></label>)}</div>;
  }
  const rows=taskRows(pc,instance);
  const t=asTurn(instance);
  const available=pc==='turn_routing'?Object.keys(t.coordinates).filter(n=>Number(n)!==t.depot&&!t.customers.some(c=>c.node===Number(n))):[];
  return <>
    <label className={s.field}>车辆容量<Input aria-label="车辆容量" type="number" min={1} value={'capacity' in instance?Number(instance.capacity):1} onChange={e=>onChange(setCapacity(instance,Number(e.target.value)))}/></label>
    <details open={rows.length<=5}><summary>任务清单 · {rows.length} 项</summary><div className={s.taskList}>{rows.map(r=><div className={s.taskRow} key={r.id}><span>{r.label}<small>{r.xy?.map(v=>v.toFixed(2)).join(', ')} {scenario.frame.units==='m'?'m':''}</small></span><label>需求<Input aria-label={`${r.label} 需求`} type="number" min={0} value={r.demand} onChange={e=>onChange(setDemand(pc,instance,r.id,Number(e.target.value)))}/></label><Button aria-label={`移除 ${r.label}`} onClick={()=>onChange(pc==='turn_routing'?toggleTurnTask(t,r.node!):removeCvrpPoint(asCvrp(instance),r.id))}>移除</Button></div>)}</div></details>
    {pc==='turn_routing'?<div className={s.row}><Select aria-label="添加任务节点" value={node} onChange={e=>setNode(e.target.value)}><option value="">选择路网节点</option>{available.map(n=><option key={n} value={n}>节点 {n} · {t.coordinates[n].join(', ')}</option>)}</Select><Button disabled={!available.includes(node)} onClick={()=>{onChange(toggleTurnTask(t,Number(node)));setNode('');}}>添加任务</Button></div>:<div className={s.formGrid}><label className={s.field}>新任务 X<Input aria-label="新任务 X" type="number" step={.1} value={x} onChange={e=>setX(Number(e.target.value))}/></label><label className={s.field}>新任务 Y<Input aria-label="新任务 Y" type="number" step={.1} value={y} onChange={e=>setY(Number(e.target.value))}/></label><Button onClick={()=>onChange(addCvrpPoint(asCvrp(instance),[x,y]))}>添加任务点</Button></div>}
  </>;
}
