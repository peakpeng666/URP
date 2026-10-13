"""Fixed handwritten unit suite under the same worker OS bounds; no model inputs."""
import io,json,os,pathlib,resource,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from runtime import require_limits,limits
require_limits()
sys.path.insert(0,str(ROOT/'tests'))
import test_handwritten_controls
suite=unittest.defaultTestLoader.loadTestsFromModule(test_handwritten_controls)
text=io.StringIO();result=unittest.TextTestRunner(stream=text,verbosity=2).run(suite)
log=text.getvalue()
if len(log.encode())>20000:raise RuntimeError('unit diagnostic bound')
out={'status':'completed_finite' if result.wasSuccessful() else 'infrastructure_failure','error':None if result.wasSuccessful() else 'handwritten assertion failure','pid':os.getpid(),'limits':limits(),'result':{'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),'log':log,'formula_domain_evidence':getattr(test_handwritten_controls,'EVIDENCE',[])}}
sys.stdout.write(json.dumps(out,allow_nan=False,separators=(',',':')));sys.stdout.flush()
if not result.wasSuccessful():raise SystemExit(1)
