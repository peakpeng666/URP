#!/usr/bin/python3
"""Parent debugger for one owned child; preserve crash evidence and bounded shutdown."""
import os, re, selectors, signal, subprocess, sys, time
p=subprocess.Popen(['gdb','-q','--interpreter=mi2','--args',*sys.argv[1:]],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
inferior=None
crashed=False
def command(s):
    p.stdin.write((s+'\n').encode());p.stdin.flush()
def stop(signum,frame):
    if inferior is not None:
        try:os.kill(inferior,signal.SIGINT)
        except ProcessLookupError:pass
signal.signal(signal.SIGINT,stop)
for c in ['-gdb-set pagination off','-gdb-set mi-async on','-interpreter-exec console "handle SIGINT nostop noprint pass"','-exec-run']:command(c)
sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
buf=b'';quit_at=None;deadline=time.monotonic()+180
while p.poll() is None:
    if time.monotonic()>deadline:
        command('-gdb-exit');break
    if quit_at and time.monotonic()>quit_at:
        command('-gdb-exit');quit_at=None
    for _,_ in sel.select(.1):
        chunk=os.read(p.stdout.fileno(),65536)
        if not chunk:continue
        sys.stdout.buffer.write(chunk);sys.stdout.buffer.flush();buf+=chunk
        while b'\n' in buf:
            raw,buf=buf.split(b'\n',1);line=raw.decode(errors='replace')
            m=re.search(r'=thread-group-started,.*pid="(\d+)"',line)
            if m:inferior=int(m[1])
            if '*stopped,reason="signal-received"' in line:
                crashed=True
                command('-interpreter-exec console "thread apply all bt 30"')
                command('-interpreter-exec console "info registers rax rdi rip"')
                command('-interpreter-exec console "x/4gx $rdi"')
                command('-interpreter-exec console "x/4gx $rax"')
                command('-interpreter-exec console "info proc mappings"')
                quit_at=time.monotonic()+2
            elif '*stopped,reason="exited' in line:command('-gdb-exit')
rc=p.wait(timeout=5)
raise SystemExit(139 if crashed else rc)
