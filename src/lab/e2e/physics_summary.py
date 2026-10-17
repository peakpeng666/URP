#!/usr/bin/env python3
"""Offline, reproducible figures and CSV from measured physics response trials."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('primary','holdout','legacy','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args(); a.out.mkdir(parents=True,exist_ok=False)
    rows, sources = [], {}
    def read(path):
        raw = path.read_bytes();sources[str(path.resolve())] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    groups = {name:read(getattr(a,name)/'summary.json') for name in ('primary','holdout','legacy')}
    for group, trials in groups.items():
        for r in trials:
            d = r['dynamics']['vehicles'][0]
            rows.append({'group':group,'case':r['case'],'repeat':r['repeat'],
                'straight_error_m':r['stages']['straight']['absolute_error_m'],
                'brake_error_m':r['stages']['brake']['absolute_error_m'],
                'spin_error_rad':r['stages']['rotate']['absolute_error_rad'],
                'odom_final_m':d['odom_position_final_m'],'odom_rmse_m':d['odom_position_rmse_m'],
                'odom_yaw_rmse_rad':d['odom_yaw_rmse_rad'],
                'reference_conformance':r.get('reference_conformance',False)})
    with (a.out/'trials.csv').open('w') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    nominal = [r for r in rows if r['group']!='legacy' and r['case']!='low_grip']
    summary = {'nominal_and_payload_trials':len(nominal),
        'nominal_and_payload_reference_passed':sum(r['reference_conformance'] for r in nominal),
        'nominal_and_payload_observed_max':{key:max(r[key] for r in nominal) for key in
            ('straight_error_m','brake_error_m','spin_error_rad','odom_final_m','odom_rmse_m')},
        'low_grip_trials': [r for r in rows if r['case']=='low_grip'],
        'scope':'three repetitions per setting with fixed inputs; descriptive ranges, not confidence intervals or statistical superiority; no real-machine calibration',
        'source_sha256':sources}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig, axes = plt.subplots(1,2,figsize=(12,4.4),layout='constrained')
    selections = [('Cylinder\n4 ms (n=1)','legacy','step4ms'), ('Sphere\n4 ms (n=3)','primary','step4ms'),
        ('Sphere\n2 ms (n=3)','primary','step2ms'), ('Sphere\n1 ms (n=3)','primary','step1ms'),
        ('+20 kg\n4 ms (n=3)','primary','loaded'), ('Friction .05\n4 ms (n=3)','primary','low_grip')]
    for i,(label,group,case) in enumerate(selections):
        values = [r['spin_error_rad'] for r in rows if r['group']==group and r['case']==case]
        med = np.median(values)
        axes[0].errorbar(i,med,yerr=[[med-min(values)],[max(values)-med]],fmt='o',capsize=4,
            color='#b44139' if group=='legacy' else '#aa7300' if case=='low_grip' else '#24669c')
    axes[0].axhline(.15,color='#777777',ls='--',lw=1,label='Reference gate (0.15 rad)')
    axes[0].set(yscale='log',ylabel='Spin absolute error [rad]',title='(a) Analytic spin reference',
                xticks=range(len(selections)),xticklabels=[s[0] for s in selections])
    axes[0].legend(loc='lower left',fontsize=8)
    axes[0].grid(axis='y',alpha=.2)
    # Pair source-stamped wheel odometry and world pose; align only the first pair.
    for folder,label,color in [(a.legacy/'step4ms-0','Cylinder (legacy)','#b44139'),
            (a.primary/'step4ms-0','Sphere (nominal)','#24669c'),
            (a.primary/'low_grip-0','Sphere (friction .05)','#aa7300')]:
        d = read(folder/'response.json')
        truth = np.asarray(d['rigid_body_poses']['vehicle_1']); odom = np.asarray(d['wheel_odometry']['vehicle_1'])
        o = odom[(odom[:,0]>=truth[0,0])&(odom[:,0]<=truth[-1,0])]
        xy = np.stack([np.interp(o[:,0],truth[:,0],truth[:,c]) for c in (1,2)],axis=1)
        yaw = np.interp(o[0,0],truth[:,0],np.unwrap(truth[:,6])) - o[0,3]
        rot = np.array([[np.cos(yaw),-np.sin(yaw)],[np.sin(yaw),np.cos(yaw)]])
        error = np.linalg.norm((o[:,1:3]-o[0,1:3])@rot.T+xy[0]-xy,axis=1)
        axes[1].plot(o[:,0]-o[0,0],error,label=f'{label}: final {error[-1]:.4f} m',color=color)
    axes[1].set(xlabel='Simulation time since first paired sample [s]',ylabel='Odometry position error [m]',
                title='(b) Wheel odometry vs world truth')
    axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    fig.suptitle('Rigid-ground differential-drive verification — synthetic model')
    for suffix in ('png','svg','pdf'):
        fig.savefig(a.out/f'physics-verification.{suffix}',dpi=220)
    summary['source_sha256'] = sources
    (a.out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('low_grip_trials','source_sha256')},indent=2))


if __name__ == '__main__':
    main()
