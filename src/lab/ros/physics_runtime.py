"""Verify the physics implementation actually loaded by owned Gazebo processes."""
import hashlib
import re
from pathlib import Path


def selection(log_path):
    log = re.sub(r'\x1b\[[0-9;]*m', '', Path(log_path).read_text(errors='replace'))
    detector = re.findall(r'Using \[([^]]+)\] collision detector', log)
    solver = re.findall(r'Using \[([^]]+)\] solver', log)
    return detector, solver


def logical_library_name(path):
    # Gazebo's unversioned plugin aliases resolve to names containing ABI majors.
    return re.sub(r'(libignition-(?:physics|gazebo))\d+-', r'\1-', Path(path).name)


def audit(physical, log_path, owned_pids):
    detector, solver = selection(log_path)
    libraries, errors = {}, []
    for pid in owned_pids:
        try:
            maps = Path(f'/proc/{pid}/maps').read_text()
        except OSError:
            continue
        for line in maps.splitlines():
            columns = line.split(None, 5)
            if len(columns) < 6 or not columns[5].startswith('/'):
                continue
            path = Path(columns[5])
            if (logical_library_name(path).startswith(('libignition-physics-dartsim-plugin.so', 'libdart.so', 'libdart-collision-',
                                      'libignition-gazebo-diff-drive-system.so', 'libignition-gazebo-pose-publisher-system.so',
                                      'libignition-gazebo-joint-controller-system.so', 'liburp_joint_state.so'))
                    and str(path) not in libraries):
                libraries[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not detector or detector[-1] != physical['collision_detector']:
        errors.append('Gazebo 未确认预期碰撞检测器；拒绝静默回退')
    if not solver or solver[-1] != 'DantzigBoxedLcpSolver':
        errors.append('Gazebo 未确认预期 Dantzig 约束求解器')
    if not any(logical_library_name(p).startswith(physical['engine']) for p in libraries):
        errors.append('所属 Gazebo 进程未加载指定的 DART 物理实现')
    if physical.get('actuator_mode') == 'torque_limited':
        for prefix in ('libignition-gazebo-joint-controller-system.so', 'liburp_joint_state.so'):
            if not any(logical_library_name(p).startswith(prefix) for p in libraries):
                errors.append('力矩执行未加载必需实现：' + prefix)
        from joint_state_runtime import LIBRARY, OUTPUT
        import json
        try:
            frozen = json.loads((OUTPUT / 'manifest.json').read_text())
            if libraries.get(str(LIBRARY)) != frozen['library_sha256']:
                errors.append('实际关节发布库与本地构建指纹不一致')
        except (OSError, KeyError, ValueError):
            errors.append('缺少关节发布库的可核验构建清单')
    return {'valid': not errors, 'errors': errors, 'collision_detector': detector[-1] if detector else None,
            'solver': solver[-1] if solver else None, 'loaded_library_sha256': libraries,
            'scope': 'owned process mappings plus Gazebo selection logs; loaded alternatives do not imply they were selected'}
