#!/usr/bin/env python3
"""Read-only AZMON Mainnet explorer. Bind loopback; put TLS proxy in front."""
import argparse,collections,http.server,json,pathlib,re,socketserver,sys,threading,time,urllib.parse
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'stratum'))
from server import RPC,GENESIS
class HTTPServer(http.server.ThreadingHTTPServer):
 daemon_threads=True
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.slots=threading.BoundedSemaphore(16)
 def process_request(self,request,address):
  if not self.slots.acquire(blocking=False):request.close();return
  try:super().process_request(request,address)
  except BaseException:self.slots.release();raise
 def process_request_thread(self,*args):
  try:super().process_request_thread(*args)
  finally:self.slots.release()
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def reply(self,status,data,kind='application/json'):
  body=json.dumps(data,allow_nan=False).encode() if kind=='application/json' else data
  self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'");self.end_headers();self.wfile.write(body)
 def do_GET(self):
  if len(self.path)>512:return self.reply(414,{'error':'Path too long'})
  ip=self.client_address[0];now=time.monotonic()
  with self.server.rate_lock:
   for key in list(self.server.rates):
    if self.server.rates[key][0]<now-60:del self.server.rates[key]
   start,count=self.server.rates.get(ip,(now,0));self.server.rates[ip]=(start,count+1)
   if count>=60 or len(self.server.rates)>4096:return self.reply(429,{'error':'Rate limited'})
  u=urllib.parse.urlsplit(self.path)
  static={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
  if u.path in static:
   name=static[u.path];kind='text/html' if name.endswith('html') else 'application/javascript' if name.endswith('js') else 'text/css'
   return self.reply(200,(pathlib.Path(__file__).parent/name).read_bytes(),kind)
  rpc=self.server.rpc.call
  try:
   if rpc('getblockhash',0)!=GENESIS:return self.reply(503,{'error':'Wrong chain; refused'})
   if u.path=='/api/status':
    info=rpc('getblockchaininfo');height=info['blocks'];tip=rpc('getblock',info['bestblockhash'],1)
    return self.reply(200,{'stage':getattr(self.server,'deployment_stage','MAINNET_PRELAUNCH_VALIDATION'),'chain':info['chain'],'height':height,'headers':info['headers'],'difficulty':info['difficulty'],'ready':not info['initialblockdownload'],'genesis':GENESIS,'tip':tip,'peers':rpc('getconnectioncount'),'warnings':info['warnings'],'observedAt':int(time.time())})
   m=re.fullmatch(r'/api/block/([0-9]{1,10}|[a-f0-9]{64})',u.path)
   if m:
    key=m[1];bh=rpc('getblockhash',int(key)) if len(key)!=64 else key;block=rpc('getblock',bh,1);total=len(block['tx']);block['tx']=block['tx'][:200];block['transactionsShown']=len(block['tx']);block['transactionCount']=total
    cb=rpc('getblock',bh,2)['tx'][0] if block.get('height')==0 else rpc('getrawtransaction',block['tx'][0],True,bh)
    block['coinbaseOutputs']=cb['vout'];return self.reply(200,block)
   return self.reply(404,{'error':'Not found; no complete address index in this version'})
  except (OSError,ValueError,RuntimeError,KeyError):return self.reply(503,{'error':'Node unavailable or block not found; no cached success is shown'})
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',default='/var/lib/azmon-mainnet');p.add_argument('--rpc-port',type=int,default=29754);p.add_argument('--port',type=int,default=29980);p.add_argument('--public-deployment',action='store_true',help='Operator phase after verified public cutover; does not start mining or change consensus');a=p.parse_args()
 srv=HTTPServer(('127.0.0.1',a.port),Handler);srv.rpc=RPC(pathlib.Path(a.data_dir)/'azmon-mainnet/.cookie',a.rpc_port);srv.rates={};srv.rate_lock=threading.Lock()
 srv.deployment_stage='MAINNET' if a.public_deployment else 'MAINNET_PRELAUNCH_VALIDATION'
 print('AZMON read-only explorer: http://127.0.0.1:%d; public exposure is configured separately'%a.port,flush=True)
 try:srv.serve_forever()
 finally:srv.server_close()
if __name__=='__main__':main()
