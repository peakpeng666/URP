"""Render the recorded comparison. Never alters data or acceptance thresholds."""
import json
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

root = Path(__file__).resolve().parent
names = [('cross_ignore', 'No ground policy'), ('cross_capped', 'Same geometry + speed cap'), ('detour_risk', 'Detour + speed cap')]
fig, axes = plt.subplots(1, 3, figsize=(12, 5.8), sharex=True, sharey=True)
for ax, (case, title) in zip(axes, names):
    result = json.loads((root/'ground-missions-delivery'/f'{case}-result.json').read_text())
    summary = json.loads((root/'ground-missions-delivery'/f'{case}-summary.json').read_text())
    plan = result['planning_solution']['routes'][0]['polyline']
    truth = np.asarray(result['rigid_body_poses']['vehicle_1'])
    odom = np.asarray(result['wheel_odometry']['vehicle_1'])
    times = odom[(odom[:,0] >= truth[0,0]) & (odom[:,0] <= truth[-1,0]),0]
    pos = np.column_stack([np.interp(times,truth[:,0],truth[:,c]) for c in (1,2)])
    yaw = np.interp(times,truth[:,0],np.unwrap(truth[:,6]))
    o = np.column_stack([np.interp(times,odom[:,0],odom[:,c]) for c in (1,2)])
    oyaw = np.interp(times,odom[:,0],np.unwrap(odom[:,3]))
    angle = yaw[0]-oyaw[0]
    rot = np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
    aligned = (o-o[0])@rot.T+pos[0]
    ax.add_patch(Rectangle((0,0),34,26,facecolor='none',edgecolor='#888888',lw=.6))
    ax.add_patch(Rectangle((18,10),12,10,facecolor='#d9c092',alpha=.45,label='Rigid low-friction patch'))
    ax.plot(*np.array(plan).T,color='#007aff',lw=3,alpha=.5,label='Planned geometry')
    ax.plot(truth[:,1],truth[:,2],color='#222222',lw=1,label='Actual body trajectory')
    ax.plot(aligned[:,0],aligned[:,1],color='#bf3c35',ls='--',lw=1.2,label='Wheel odometry (initial alignment)')
    ax.scatter([24,30],[14,22],marker='x',color='#222222',s=35,zorder=6)
    ax.set_title(f"{title}\nMax wheel/truth divergence: {summary['divergence_m']:.2f} m",fontsize=10)
    ax.set(xlabel='x [m]',xlim=(-1,35),ylim=(-9,30),aspect='equal')
    ax.grid(alpha=.16)
axes[0].set_ylabel('y [m]')
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.01),ncols=2,fontsize=8)
fig.suptitle('Ground-aware planning: recorded physical execution, 34 × 26 m synthetic field\n'
             'Rigid Coulomb proxy; one engineering trial per policy; no tyre/soil calibration',fontsize=11)
fig.subplots_adjust(left=.06,right=.99,top=.80,bottom=.22,wspace=.10)
fig.savefig(root/'ground-comparison.png',dpi=180)
fig.savefig(root/'ground-comparison.svg')
