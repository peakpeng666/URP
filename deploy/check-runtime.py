#!/usr/bin/env python3
"""Read-only dependency diagnostics and bounded synthetic checks, not physical acceptance."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def command_check(name, command, timeout=30):
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                errors='replace', timeout=timeout)
        return dict(name=name, passed=result.returncode == 0, returncode=result.returncode,
                    stdout=result.stdout, stderr=result.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(name=name, passed=False, error=f'{type(exc).__name__}: {exc}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--components', choices=('workbench', 'research', 'full'), default='full')
    parser.add_argument('--fields2cover', choices=('auto', 'required', 'skip'))
    parser.add_argument('--output', required=True, type=Path, help='New absolute evidence directory')
    args = parser.parse_args()
    f2c_mode = args.fields2cover or ('required' if args.components == 'full' else 'auto')
    if args.components == 'full' and f2c_mode != 'required':
        parser.error('full requires Fields2Cover; choose a reduced component set instead')
    if not args.output.is_absolute() or args.output.exists():
        parser.error('--output must be a new absolute directory')
    args.output.mkdir(parents=True, exist_ok=False)
    python = ROOT / '.venv/bin/python'
    lab_python = ROOT / 'src/lab/.venv/bin/python'
    checks = []
    version = ('import sys; print(sys.executable, sys.version); '
               'assert sys.version_info[:3] == (3,12,13), "expected locked CPython 3.12.13"; ')
    checks.append(command_check('root-python-solvers', [str(python), '-c', version +
                  'import numpy, jsonschema, pyvrp; from ortools.constraint_solver import pywrapcp; '
                  'solver = pywrapcp.Solver("runtime-check")']))
    checks.append(command_check('lab-python-core', [str(lab_python), '-c', version +
                  'import fastapi, uvicorn, numpy, scipy, shapely, pyvrp, pyproj, cv2; '
                  'from ortools.constraint_solver import pywrapcp; solver = pywrapcp.Solver("runtime-check"); '
                  'from ompl import base as ob, geometric as og; space = ob.RealVectorStateSpace(2); '
                  'bounds = ob.RealVectorBounds(2); bounds.setLow(0); bounds.setHigh(1); '
                  'space.setBounds(bounds); setup = og.SimpleSetup(space)']))
    checks.append(command_check('node-version', ['node', '-e',
                  'console.log(process.version);if(process.version!=="v24.22.0")process.exit(1)']))
    checks.append(dict(name='frontend-build', passed=(ROOT / 'src/frontend/dist/index.html').is_file()))
    if args.components in ('research', 'full'):
        checks.append(command_check('native-cvrp-synthetic-smoke',
                      [sys.executable, str(ROOT / 'deploy/check-cohort.py'), '--output', str(args.output / 'cohort')], timeout=30))
    else:
        checks.append(dict(name='native-cvrp-synthetic-smoke', passed=None, status='not_selected'))
    if f2c_mode == 'auto':
        probe = command_check('fields2cover-presence', [str(lab_python), '-c',
                              'import importlib.util; raise SystemExit(0 if importlib.util.find_spec("fields2cover") else 3)'])
        if probe.get('returncode') == 3:
            checks.append(dict(name='fields2cover', passed=None, status='optional_missing'))
        elif not probe['passed']:
            checks.append(probe)
        else:
            checks.append(command_check('fields2cover', [str(lab_python), str(ROOT / 'deploy/check-fields2cover.py')]))
    elif f2c_mode == 'required':
        checks.append(command_check('fields2cover', [str(lab_python), str(ROOT / 'deploy/check-fields2cover.py')]))
    else:
        checks.append(dict(name='fields2cover', passed=None, status='not_selected'))
    if args.components in ('workbench', 'full'):
        checks.append(command_check('ros-gazebo-command-load', ['bash', '--noprofile', '--norc', '-c',
                      'source /opt/ros/humble/setup.bash && '
                      '/usr/bin/python3 -c "import rclpy" && '
                      'ros2 pkg prefix ros_gz_bridge && ros2 pkg prefix foxglove_bridge && '
                      'command -v ign && ign gazebo --versions']))
    else:
        checks.append(dict(name='ros-gazebo-command-load', passed=None, status='not_selected'))
    report = dict(schema='urp.runtime-diagnostics/1', components=args.components,
                  fields2cover=f2c_mode, created_utc=datetime.now(timezone.utc).isoformat(),
                  passed=all(c['passed'] is not False for c in checks), checks=checks,
                  not_tested=['Gazebo physical execution', 'Fuel asset availability and licensing',
                              'display/GPU drivers', 'historical NAS environments', 'formal research reproduction'])
    path = args.output / 'runtime.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    for check in checks:
        print(f"{check['name']}: " + ('PASS' if check['passed'] is True else
              ('FAIL' if check['passed'] is False else check['status'])))
    print(f'Diagnostics saved: {path}')
    print('This checks dependency loading and synthetic solvers, NOT physical Gazebo acceptance.')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
