#!/usr/bin/python3
"""CPU-only GDB parent captures its own child, then terminates only that child."""
import json
from pathlib import Path
import subprocess
import time

base=Path(__file__).resolve().parents[1]
with (base/'logs/tf-repro-gdb-final.log').open('w') as log:
    p=subprocess.Popen(['gdb','-q','--interpreter=mi2','--args',
                        str(base/'runtime/tf-repro/tf-repro')],
                       stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
    def send(command):
        p.stdin.write(command+'\n');p.stdin.flush()
    send('-gdb-set pagination off');send('-gdb-set mi-async on');send('-exec-run')
    time.sleep(4)
    send('-exec-interrupt');time.sleep(.5)
    send('-interpreter-exec console "thread apply all bt 20"');time.sleep(.5)
    send('-interpreter-exec console "set confirm off"')
    send('-interpreter-exec console "kill"');send('-gdb-exit');p.wait(timeout=5)
out=[]
for line in (base/'logs/tf-repro-gdb-final.log').read_text().splitlines():
    if line.startswith('~"'):
        try:out.append(json.loads(line[1:]))
        except ValueError:pass
(base/'logs/tf-repro-stacks-final.txt').write_text(''.join(out))
print('Diagnostic child exited; final stack saved.')
