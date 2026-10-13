/* Local text/CSV adapters only. No language model, geocoding, or inferred map geometry. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.CVRPInput=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function parseRequirements(raw){const text=String(raw).trim(),out={parser:'local_rules',capacity:null,family:null,n:null,fleet:'unlimited_identical_vehicles',warnings:[],requiresGeometryConfirmation:false};if(!text){out.warnings.push('请输入需求，或直接编辑结构化任务');return out;}
    const capacity=text.match(/(?:容量|capacity)\s*[:：=为]?\s*(\d+)/i);if(capacity)out.capacity=Number(capacity[1]);const count=text.match(/(\d+)\s*(?:个)?(?:任务点|客户点|客户)/);if(count)out.n=Number(count[1]);if(/聚类|cluster/i.test(text))out.family='clustered';else if(/均匀|uniform/i.test(text))out.family='uniform';
    const fleet=text.match(/(?:车辆数|车队规模)\s*[:：=为]?\s*(\d+)|(\d+)\s*辆车/);if(fleet&&!/车辆数不限|不限车辆|不限数量|unlimited/i.test(text)){out.fleet='finite_unsupported';out.fleetRequested=Number(fleet[1]||fleet[2]);out.warnings.push('有限车队尚未实现，请明确改为不限车辆后运行');}
    if(/时间窗|时窗|避障|道路|返航电量|充电|动态障碍|转弯半径/.test(text))out.warnings.push('提到的道路/运动/时间约束当前未建模，不能据本方案保证满足');
    if(/地址|地块|果园|地图|经纬|定位|卫星|真实/.test(text)&&!/合成|示例|synthetic/i.test(text)){out.requiresGeometryConfirmation=true;out.warnings.push('没有地理编码或地图识别后端，未推断真实坐标；需核对现有坐标后确认使用');}
    if(!capacity&&!count&&!out.family)out.warnings.push('未提取到容量、任务数或分布；保留当前可编辑参数');return out;
  }
  function parsePoints(raw){const rows=String(raw).trim().split(/\r?\n/).filter(x=>x.trim());if(rows[0]?.trim().toLowerCase()==='x,y,demand')rows.shift();const coordinates=[],demands=[];for(const [j,line] of rows.entries()){const values=line.split(',').map(s=>s.trim());if(values.length!==3||values.some(s=>s===''))throw Error('第 '+(j+1)+' 行须为 x,y,demand');const [x,y,d]=values.map(Number);coordinates.push([x,y]);demands.push(d);}return {coordinates,demands};}
  return {parseRequirements,parsePoints};
});
