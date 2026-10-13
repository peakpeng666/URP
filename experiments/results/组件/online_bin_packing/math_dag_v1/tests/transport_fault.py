"""Fixed trusted transport faults only; never accepts code or graph arguments."""
import os,sys,time
mode=sys.argv[1]
sys.stdin.buffer.read(100001)
if mode=='stdout_bound':os.write(1,b'x'*400001)
elif mode=='stderr_bound':os.write(2,b'x'*16385)
elif mode=='eof_hang':
 os.close(1);os.close(2);time.sleep(2)
elif mode=='malformed':os.write(1,b'{')
elif mode=='duplicate':os.write(1,b'{"status":0,"status":1}')
elif mode=='nonfinite':os.write(1,b'{"extra":1e9999}')
elif mode=='nonzero':
 os.write(1,b'{"status":"completed_finite"}');raise SystemExit(3)
else:raise ValueError('fixed fault mode')
