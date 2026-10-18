import os
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ros'))
from physical_session_lock import PhysicsBusy, physical_session


def test_two_processes_cannot_start_physics_and_crash_releases_kernel_lock(tmp_path):
    lock = tmp_path / 'physical.lock'
    code = '''import os,sys
from physical_session_lock import physical_session, PhysicsBusy
try:
 with physical_session(sys.argv[1]):
  print('acquired', flush=True)
  if len(sys.argv)>2: sys.stdin.readline(); os._exit(7)
except PhysicsBusy as e:
 print(e); sys.exit(2)
'''
    env = {**os.environ, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'ros')}
    holder = subprocess.Popen([sys.executable, '-c', code, str(lock), 'hold'], env=env,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == 'acquired'
        refused = subprocess.run([sys.executable, '-c', code, str(lock)], env=env,
                                 capture_output=True, text=True, timeout=5)
        assert refused.returncode == 2 and '拒绝并发启动' in refused.stdout
        assert holder.poll() is None
        holder.communicate('\n', timeout=5)
        assert holder.returncode == 7
        with physical_session(lock):
            with pytest.raises(PhysicsBusy):
                with physical_session(lock):
                    pass
    finally:
        if holder.poll() is None:
            holder.communicate('\n', timeout=5)
