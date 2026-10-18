"""Draw bounded physical contrasts from saved audit summaries; no fitted model."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
rows = json.loads((OUT / 'physical-cases.json').read_text())
rounds = ('coplanar-v4', 'coplanar-repeat73', 'coplanar-repeat74', 'release', 'guard-release')
data = []
for i, name in enumerate(rounds, 1):
    for case in ('geometry_control', 'ground_low'):
        row = next(r for r in rows if r['round'] == name and r['case'] == case)
        data.append({'repeat': i, 'round': name, 'case': case,
                     'max_wheel_truth_m': row['wheel_truth_max_m'],
                     'zone_contact_entries': row['zone_contact_entries'],
                     'session_id': row['session_id']})
with (OUT / 'friction-contrast.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=list(data[0]))
    writer.writeheader()
    writer.writerows(data)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'svg.fonttype': 'none', 'pdf.fonttype': 42})
fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.6), layout='constrained')
for i in range(len(rounds)):
    pair = data[2*i:2*i+2]
    a.plot([0, 1], [r['max_wheel_truth_m'] for r in pair], 'o-', lw=1.1,
           label=f'Repetition {i+1}')
a.set_yscale('log')
a.set_xticks([0, 1], ['Coplanar tiles\nμ=1.0', 'Same geometry\nμ=0.12'])
a.set_ylabel('Maximum wheel / truth position disagreement (m)')
a.set_title('A. Friction changes actual execution')
a.grid(axis='y', alpha=.2)
a.legend(frameon=False, fontsize=8)

labels = ('localization', 'combined', 'outage_hold', 'severe')
for i, name in enumerate(('guard-release',)):
    group = [next(r for r in rows if r['round'] == name and r['case'] == c) for c in labels]
    x = list(range(4))
    bars = b.bar(x, [r['metrics']['localization_position_error_mean_m'] for r in group],
                 width=.55, label='Final guard, observation seed 72')
    for bar, row in zip(bars, group):
        b.annotate(f"{row['metrics']['tasks_verified']}/3", (bar.get_x()+bar.get_width()/2, bar.get_height()),
                   xytext=(0, 3), textcoords='offset points', ha='center', fontsize=8)
b.set_xticks(range(4), ['Position\nerrors', 'Friction +\nposition errors', 'Outage +\nrecovery', 'Severe\nerrors'])
b.set_ylabel('Mean estimated / truth position error (m)')
b.set_title('B. Truth service gate distinguishes failure')
b.legend(frameon=False, fontsize=8)
b.grid(axis='y', alpha=.2)
fig.suptitle('URP non-ideal execution audit — synthetic, uncalibrated models', fontsize=12)
fig.supxlabel('A: five sessions per condition (truth control); B: final guard, labels are truth-verified tasks.\nSame frozen route within each run; no population confidence or agricultural calibration claim.', fontsize=9)
fig.savefig(OUT / 'physical-evidence.png', dpi=240)
fig.savefig(OUT / 'physical-evidence.pdf')
plt.close(fig)
