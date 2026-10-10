"""Fresh Codex app-server registration check; no model request required."""
import json, subprocess, select, time, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
state = tempfile.TemporaryDirectory(prefix="ig-codex-discovery-")
p=subprocess.Popen(['codex','--no-daemon','-c',f'sqlite_home="{state.name}/state"','-c',f'log_dir="{state.name}/log"','app-server','--stdio'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=open(Path(state.name)/'stderr.log','w'),text=True)
def send(v):
 p.stdin.write(json.dumps(v)+'\n');p.stdin.flush()
def response(i):
 deadline=time.monotonic()+30
 while time.monotonic()<deadline:
  if select.select([p.stdout],[],[],1)[0]:
   line=p.stdout.readline()
   if not line: raise RuntimeError('server stopped: '+(Path(state.name)/'stderr.log').read_text())
   v=json.loads(line)
   if v.get('id')==i:return v
 raise TimeoutError('app-server response')
try:
 send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'ig-skill-test','version':'1.0'}}})
 assert 'result' in response(1)
 send({'method':'initialized'})
 send({'id':2,'method':'skills/list','params':{'cwds':[str(ROOT)],'forceReload':True}})
 v=response(2)
 assert 'result' in v, v
 skills = v['result']['data'][0]['skills']
 for name in ('ig-reel', 'ig-human'):
  match = next((s for s in skills if s['name'] == name and s['enabled']), None)
  assert match is not None, f'{name} not discovered as an enabled unqualified skill'
  print(json.dumps({k:match[k] for k in ('name','scope','path','enabled')},ensure_ascii=False))
finally:
 p.terminate();p.wait(timeout=10)
 state.cleanup()
