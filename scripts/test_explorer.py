#!/usr/bin/env python3
"""Exercise explorer HTTP boundary, errors and resource caps without exposing RPC."""
import importlib.util,json,pathlib,sys,threading,urllib.request,urllib.error
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'stratum'))
spec=importlib.util.spec_from_file_location('rc_explorer',root/'explorer/server.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
class Fake:
 def __init__(self):self.bad=False;self.calls=[]
 def call(self,method,*p):
  self.calls.append(method)
  if method=='getblockhash':return 'f'*64 if self.bad else e.GENESIS
  if method=='getblockchaininfo':return dict(blocks=3,headers=3,chain='main',difficulty=.0039,initialblockdownload=False,bestblockhash='a'*64,warnings=[])
  if method=='getconnectioncount':return 2
  if method=='getblock':return dict(hash='a'*64,tx=['b'*64]*250,height=3)
  if method=='getrawtransaction':return dict(vout=[{'value':250,'scriptPubKey':{'address':'az1fixture'}}])
  raise AssertionError(method)
s=e.HTTPServer(('127.0.0.1',0),e.Handler);s.rpc=Fake();s.rates={};s.rate_lock=threading.Lock();threading.Thread(target=s.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(s.server_port)
def get(path):
 try:
  with urllib.request.urlopen(base+path) as r:return r.status,r.read(),r.headers
 except urllib.error.HTTPError as r:return r.code,r.read(),r.headers
try:
 code,data,headers=get('/api/status');assert code==200 and json.loads(data)['height']==3;assert 'no-store' in headers['Cache-Control']
 code,data,_=get('/api/block/3');b=json.loads(data);assert code==200 and b['transactionCount']==250 and b['transactionsShown']==200
 assert get('/api/wallet/sendtoaddress')[0]==404
 s.rpc.bad=True;assert get('/api/status')[0]==503;s.rpc.bad=False
 assert get('/'+('x'*600))[0]==414
 with s.rate_lock:s.rates['127.0.0.1']=(__import__('time').monotonic(),60)
 assert get('/api/status')[0]==429
 assert not any(x in s.rpc.calls for x in ['sendtoaddress','dumpprivkey','walletpassphrase','stop'])
 report={'status':'PASS','checks':['Read-only HTTP route allowlist','Wrong genesis fails closed','Transaction-list cap 200','Rate limit and path-length cap','RPC failures never return fake live data','No wallet/write RPC methods called'],'limitations':'Mock RPC boundary tests; real node API is tested by test_explorer_live.py'}
 (root/'reports/explorer.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:s.shutdown();s.server_close()
