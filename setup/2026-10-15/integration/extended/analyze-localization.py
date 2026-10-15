import json,pathlib,math,sys
import numpy as np
from scipy.ndimage import distance_transform_edt
sys.path.insert(0,'src/lab')
from urp_lab.scenarios import maps
p=pathlib.Path(sys.argv[1]);g=maps.load(sys.argv[2] if len(sys.argv)>2 else 'warehouse');dt=distance_transform_edt(g.free)*g.resolution
rows=[]
for f in sorted(p.glob('scan-*-leg-*.json')):
 s=json.loads(f.read_text());robot=s['robot'];scores={}
 for key,pose in [('truth',robot['ground_truth']),('localized',robot['localized'][1:])]:
  x,y,a=pose;x-=.04*math.cos(a);y-=.04*math.sin(a);values=[]
  for i,d in enumerate(s['ranges']):
   if d is None or not .2<d<11.9:continue
   angle=a+math.pi/2+s['angle_min']+i*s['angle_increment'];r,c=g.rc(x+d*math.cos(angle),y+d*math.sin(angle))
   if 0<=r<g.height and 0<=c<g.width:values.append(float(dt[r,c]))
  scores[key]={'mean':sum(values)/len(values),'p95':float(np.quantile(values,.95)),'count':len(values)}
 rows.append(dict(file=f.name,robot=robot,scan_scores=scores))
print(json.dumps(rows,indent=2))
