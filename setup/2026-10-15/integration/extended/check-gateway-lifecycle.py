"""Run only with port 4100 free. Start and reap only our own gateway children."""
import json,pathlib,socket,subprocess,time,urllib.request,urllib.error
root=pathlib.Path(__file__).resolve().parents[4];out=pathlib.Path(__file__).parent
base='http://127.0.0.1:4100';rows=[]
def get():
 try:
  with urllib.request.urlopen(base+'/lab/api/health',timeout=.5) as r:return json.load(r)
 except (OSError,urllib.error.URLError):return None
if get():raise SystemExit('Gateway already running; stop it explicitly before this test')
for i in range(2):
 with (out/f'gateway-lifecycle-{i+1}.log').open('w') as log:
  p=subprocess.Popen(['bash','setup/run.sh','lab'],cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  end=time.monotonic()+20
  while not get() and p.poll() is None and time.monotonic()<end:time.sleep(.1)
  assert get() and p.poll() is None,'owned gateway failed to start'
  request=urllib.request.Request(base+'/lab/api/shutdown',data=b'{}',headers={'Content-Type':'application/json'},method='POST')
  with urllib.request.urlopen(request,timeout=5) as r:response=json.load(r)
  code=p.wait(timeout=20)
  rows.append(dict(cycle=i+1,pid=p.pid,response=response,actual_child_returncode=code,health_after=get()))
  (out/'gateway-lifecycle.json').write_text(json.dumps(dict(cases=rows,scope='direct Popen waitpid; actual gateway process, not tool shell wrapper',earlier_tool_shell_returncode=143),ensure_ascii=False,indent=2))
  print(rows[-1],flush=True)
  assert code==0 and get() is None,rows[-1]
