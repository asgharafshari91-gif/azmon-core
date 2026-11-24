#!/usr/bin/env python3
"""Real final-genesis node and read-only Explorer, without mining or funds."""
import argparse,importlib.util,json,pathlib,subprocess,sys,tempfile,threading,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'stratum'));sys.path.insert(0,str(ROOT/'scripts'))
from server import RPC
from test_utils import free_port,wait
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=pathlib.Path,default=ROOT/'build');a=p.parse_args()
g=json.loads((ROOT/'genesis.json').read_text())
spec=importlib.util.spec_from_file_location('azmon_explorer_live',ROOT/'explorer/server.py');explorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(explorer)
with tempfile.TemporaryDirectory(prefix='azmon-explorer-') as d:
 data=pathlib.Path(d);rpc_port=free_port();log=(data/'node.log').open('w')
 node=subprocess.Popen([str(a.build.resolve()/'bin/bitcoind'),'-datadir='+str(data),'-chain=main','-server=1','-listen=0','-dnsseed=0','-fixedseeds=0','-discover=0','-listenonion=0','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1','-rpcport='+str(rpc_port),'-printtoconsole=0'],stdout=log,stderr=log)
 rpc=RPC(data/'azmon-mainnet/.cookie',rpc_port);http=None
 try:
  wait(lambda:rpc.call('getblockhash',0)==g['hash'])
  http=explorer.HTTPServer(('127.0.0.1',0),explorer.Handler);http.rpc=rpc;http.rates={};http.rate_lock=threading.Lock()
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  def get(path):
   with urllib.request.urlopen('http://127.0.0.1:'+str(http.server_port)+path,timeout=15) as response:return json.loads(response.read())
  status=get('/api/status');assert status['genesis']==g['hash'] and status['height']==0 and status['stage']=='MAINNET_PRELAUNCH_VALIDATION'
  block=get('/api/block/0');assert block['hash']==g['hash'] and block['coinbaseOutputs'][0]['value']==0
  assert block['coinbaseOutputs'][0]['scriptPubKey']['hex']=='6a'
  http.deployment_stage='MAINNET';assert get('/api/status')['stage']=='MAINNET'
  report={'status':'PASS','scope':'Actual final-genesis node on Linux loopback','checks':['Explorer status pins the actual new genesis','Genesis block detail is readable without getrawtransaction genesis failure','Genesis reward is zero and its output is OP_RETURN','Operator deployment phase changes metadata only; chain identity remains verified'],'publicDeployment':False}
  (ROOT/'reports/explorer-live.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 finally:
  if http:http.shutdown();http.server_close()
  try:rpc.call('stop')
  except Exception:node.terminate()
  try:node.wait(timeout=30)
  except subprocess.TimeoutExpired:node.kill();node.wait()
  log.close()
