"""Exercise a real launch leader that forwards SIGINT to its child."""
import json
from pathlib import Path
import subprocess
import sys


def test_launch_shutdown_delivers_sigint_once_and_reaps_descendants(tmp_path):
    # Run the subreaper in isolation so pytest never adopts another test's child.
    child = tmp_path / 'child.py'
    child.write_text('''import signal, sys, time
from pathlib import Path
root = Path(sys.argv[1])
count = 0
def stop(*_):
    global count
    count += 1
signal.signal(signal.SIGINT, stop)
(root / 'ready').touch()
while not count:
    time.sleep(.01)
time.sleep(.15)
(root / 'count').write_text(str(count))
''')
    leader = tmp_path / 'leader.py'
    leader.write_text('''import signal, subprocess, sys
child = subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])
signal.signal(signal.SIGINT, lambda *_: child.send_signal(signal.SIGINT))
raise SystemExit(child.wait())
''')
    driver = tmp_path / 'driver.py'
    driver.write_text('''import json, os, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import processes
root = Path(sys.argv[2])
processes.BASE = root
(root / 'logs').mkdir()
owned = processes.OwnedProcesses(dict(os.environ), 'test')
owned.start('sim', [sys.executable, str(root / 'leader.py'), str(root / 'child.py'), str(root)])
try:
    end = time.monotonic() + 5
    while not (root / 'ready').exists():
        if time.monotonic() > end:
            raise TimeoutError('launch child not ready')
        time.sleep(.01)
finally:
    report = owned.cleanup()
print(json.dumps({'cleanup': report, 'remaining': owned.sample()}))
''')
    result = subprocess.run([sys.executable, str(driver), str(Path(__file__).parents[1] / 'ros'), str(tmp_path)],
                            check=True, capture_output=True, text=True, timeout=30)
    report = json.loads(result.stdout)
    assert (tmp_path / 'count').read_text() == '1'
    assert report['remaining'] == []
    assert report['cleanup'][0]['complete']
    assert all(row['returncode'] == 0 for row in report['cleanup'][0]['reaped'])
