#!/usr/bin/python3
"""Run one owned diagnostic child under GDB and capture two bounded stacks."""
import os
import selectors
import signal
import subprocess
import sys
import time

p = subprocess.Popen(['gdb', '-q', '--interpreter=mi2', '--args', *sys.argv[1:]],
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     text=True, bufsize=1)
def command(value):
    p.stdin.write(value+'\n'); p.stdin.flush()
command('-gdb-set pagination off')
command('-gdb-set mi-async on')
command('-exec-run')
start = time.monotonic()
deadlines = iter([25, 85])
next_at = next(deadlines, float('inf'))
resume_at = None
selector = selectors.DefaultSelector()
selector.register(p.stdout, selectors.EVENT_READ)
def stop(signum, frame):
    try: command('-exec-interrupt')
    except (BrokenPipeError, OSError): pass
signal.signal(signal.SIGINT, stop)
while p.poll() is None:
    now = time.monotonic()
    if now-start >= next_at:
        print('URP_THREAD_SNAPSHOT', now-start, flush=True)
        command('-exec-interrupt')
        resume_at = now+1
        next_at = next(deadlines, float('inf'))
    if resume_at is not None and now>=resume_at:
        command('-interpreter-exec console "thread apply all bt 25"')
        command('-exec-continue')
        resume_at = None
    for key, _ in selector.select(.1):
        line = key.fileobj.readline()
        if line:
            print(line, end='', flush=True)
            if '*stopped,reason="exited' in line:
                command('-gdb-exit')
sys.exit(p.wait())
