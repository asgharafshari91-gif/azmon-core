#!/usr/bin/env python3
"""AZMON Mainnet SOLO Stratum V1. Experimental; not a shared-reward pool."""
import hmac,os
import argparse,asyncio,base64,hashlib,json,logging,pathlib,re,secrets,ssl,struct,time,urllib.request,urllib.error,sqlite3
from metrics import Metrics
GENESIS='000000057eacbad83bbf08d90a98403e0bcfc5bd8566fb9d92962786096d274c'
# Unused testnet API constants removed.
DIFF1=0xffff<<208
LOG=logging.getLogger('azmon-stratum')
def sha(b):return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def varint(n):
 if n<253:return bytes([n])
 if n<=65535:return b'\xfd'+struct.pack('<H',n)
 return b'\xfe'+struct.pack('<I',n)
def scriptnum(n):
 if 1<=n<=16:return bytes([0x50+n])
 b=n.to_bytes((n.bit_length()+7)//8,'little') or b'\x00'
 if b[-1]&128:b+=b'\x00'
 return bytes([len(b)])+b
def swapwords(b):return b''.join(b[i:i+4][::-1] for i in range(0,len(b),4))
def target(bits):
 v=int(bits,16);return (v&0x7fffff)<<(8*((v>>24)-3))
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Redirect refused')
OPENER=urllib.request.build_opener(NoRedirect())
def request(url,body,headers):
 req=urllib.request.Request(url,json.dumps(body).encode(),headers)
 with OPENER.open(req,timeout=10) as r:return json.loads(r.read(8*1024*1024))
class RPC:
 def __init__(self,cookie,port):self.cookie=pathlib.Path(cookie);self.port=port
 def call(self,method,*params):
  auth=base64.b64encode(self.cookie.read_bytes().strip()).decode()
  r=request('http://127.0.0.1:%d/'%self.port,{'jsonrpc':'2.0','id':1,'method':method,'params':list(params)},{'Authorization':'Basic '+auth,'Content-Type':'application/json'})
  if r.get('error'):raise RuntimeError(str(r['error']))
  return r['result']
 async def __call__(self,method,*params):return await asyncio.to_thread(self.call,method,*params)
WORKERS=None
async def authorize(worker,token):
 if not WORKERS or not re.fullmatch(r'[a-f0-9-]{36}',worker) or not re.fullmatch(r'[a-f0-9]{64}',token):return None
 # Re-read for immediate revocation, never store plaintext worker keys.
 try:
  entries=json.loads(pathlib.Path(WORKERS).read_text())
  row=entries.get(worker,{})
  if row.get('enabled') is not True:return None
  if not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(),row.get('tokenHash','')):return None
  return row.get('address')
 except (OSError,ValueError,TypeError):return None
class Job:
 def __init__(self,t,address_script):
  self.t=t;self.id=secrets.token_hex(8);self.created=time.time();self.seen=set()
  prefix=scriptnum(t['height'])+b'\x06/AZMN/'
  script_len=len(prefix)+8+4
  self.c1=b'\x01\x00\x00\x00\x01'+b'\x00'*32+b'\xff'*4+varint(script_len)+prefix
  outputs=[struct.pack('<Q',t['coinbasevalue'])+varint(len(address_script))+address_script]
  self.witness=bool(t.get('default_witness_commitment'))
  if self.witness:
   commitment=bytes.fromhex(t['default_witness_commitment']);outputs.append(b'\x00'*8+varint(len(commitment))+commitment)
  self.c2=b'\xff'*4+varint(len(outputs))+b''.join(outputs)+b'\x00'*4
  # Branch for leaf zero; placeholder zero never enters its own branch.
  hashes=[b'\x00'*32]+[bytes.fromhex(tx['txid'])[::-1] for tx in t['transactions']];self.branch=[]
  while len(hashes)>1:
   if len(hashes)%2:hashes.append(hashes[-1])
   self.branch.append(hashes[1]);hashes=[sha(hashes[i]+hashes[i+1]) for i in range(0,len(hashes),2)]
 def notify(self):
  t=self.t
  return [self.id,swapwords(bytes.fromhex(t['previousblockhash'])[::-1]).hex(),self.c1.hex(),self.c2.hex(),[x.hex() for x in self.branch],f"{t['version']:08x}",t['bits'],f"{t['curtime']:08x}",True]
 def candidate(self,extra1,extra2,ntime,nonce):
  cb=self.c1+extra1+bytes.fromhex(extra2)+self.c2;root=sha(cb)
  for h in self.branch:root=sha(root+h)
  header=struct.pack('<I',self.t['version'])+bytes.fromhex(self.t['previousblockhash'])[::-1]+root+struct.pack('<III',int(ntime,16),int(self.t['bits'],16),int(nonce,16))
  if self.witness:full=cb[:4]+b'\x00\x01'+cb[4:-4]+b'\x01\x20'+b'\x00'*32+cb[-4:]
  else:full=cb
  block=header+varint(1+len(self.t['transactions']))+full+b''.join(bytes.fromhex(x['data']) for x in self.t['transactions'])
  return sha(header),block
class Pool:
 def __init__(self,rpc,journal,auth=authorize):
  self.rpc=rpc;self.auth=auth;self.clients=set();self.template=None
  self.db=sqlite3.connect(journal);self.db.execute('create table if not exists shares(hash text primary key,worker text,height integer,status text,created integer)');self.db.commit()
  self.metrics=Metrics(self.db,str(journal)+'.metrics.json')
 async def refresh(self):
  if await self.rpc('getblockhash',0)!=GENESIS:raise RuntimeError('Wrong genesis: only AZMON Mainnet is supported')
  self.template=await self.rpc('getblocktemplate',{'rules':['segwit']})
 async def poll(self):
  while True:
   await asyncio.sleep(15)
   try:
    await self.refresh()
    for c in list(self.clients):
     if c.worker:
      try:await c.new_job()
      except Exception:c.writer.close()
   except Exception as e:
    self.template=None
    LOG.warning('Node unavailable; jobs paused (%s)',type(e).__name__)
    for c in list(self.clients):c.jobs.clear()
 async def publish_metrics(self):
  while True:
   try:self.metrics.emit(self.clients,self.template,GENESIS)
   except Exception as e:LOG.warning('Metrics write failed (%s)',type(e).__name__)
   await asyncio.sleep(5)
 async def connect(self,reader,writer):
  if len(self.clients)>=32:writer.close();return
  c=Client(self,reader,writer);self.clients.add(c)
  try:await c.run()
  finally:
   self.clients.discard(c);writer.close()
   if c.metered:self.metrics.touch(c.worker)
   self.metrics.emit(self.clients,self.template,GENESIS)
   try:await writer.wait_closed()
   except (ConnectionError,OSError):pass
 async def run(self,host,port,tls=None):
  await self.refresh()
  self.server=await asyncio.start_server(self.connect,host,port,ssl=tls,limit=16384)
  self.poll_task=asyncio.create_task(self.poll())
  self.metrics_task=asyncio.create_task(self.publish_metrics())
  LOG.info('AZMON Mainnet SOLO listening on %s:%s; no shared payouts',host,port)
  try:
   async with self.server:await self.server.serve_forever()
  finally:self.poll_task.cancel();self.metrics_task.cancel();self.db.close()
class Client:
 def __init__(self,pool,reader,writer):
  self.pool=pool;self.reader=reader;self.writer=writer;self.extra=secrets.token_bytes(8);self.subscribed=False;self.worker=None;self.token=None;self.jobs={};self.auth_at=0;self.address=None;self.calls=[];self.metered=False
 async def send(self,obj):self.writer.write((json.dumps(obj)+'\n').encode());await asyncio.wait_for(self.writer.drain(),10)
 async def reply(self,id,result=None,error=None):
  if error and self.metered:self.pool.metrics.reject(self.worker)
  await self.send({'id':id,'result':result,'error':error})
 async def notify(self,m,p):await self.send({'id':None,'method':m,'params':p})
 async def new_job(self):
  address=await self.pool.auth(self.worker,self.token)
  if not address:raise ValueError('Worker disabled or invalid token')
  self.address=address;self.auth_at=time.time()
  info=await self.pool.rpc('validateaddress',address)
  if not info.get('isvalid') or not address.startswith('az1'):raise ValueError('Invalid AZMON payout address')
  t=self.pool.template
  if not t:raise ValueError('Node unavailable')
  j=Job(t,bytes.fromhex(info['scriptPubKey']));self.jobs={j.id:j}
  # A fixed network-difficulty target: each accepted share is a block candidate.
  # Production VarDiff and hardware-specific minimums are deliberately unsupported.
  await self.notify('mining.set_difficulty',[DIFF1/target(t['bits'])])
  await self.notify('mining.notify',j.notify())
  self.metered=True;self.pool.metrics.touch(self.worker)
  self.pool.metrics.emit(self.pool.clients,self.pool.template,GENESIS)
 async def run(self):
  try:
   while True:
    raw=await asyncio.wait_for(self.reader.readline(),3600 if self.worker else 30)
    if not raw:break
    now=time.monotonic();self.calls=[t for t in self.calls if now-t<1]
    if len(self.calls)>=20:break
    self.calls.append(now)
    try:
     msg=json.loads(raw);id=msg.get('id');method=msg.get('method');p=msg.get('params',[])
     if not isinstance(p,list):raise ValueError()
     if method=='mining.subscribe':
      if self.subscribed:await self.reply(id,error=[20,'Already subscribed',None]);continue
      self.subscribed=True;await self.reply(id,[[['mining.notify',self.extra.hex()]],self.extra.hex(),4])
     elif method=='mining.configure':await self.reply(id,{'version-rolling':False,'minimum-difficulty':False})
     elif method=='mining.ping':await self.reply(id,True)
     elif method=='mining.extranonce.subscribe':await self.reply(id,False)
     elif method=='mining.authorize':
      if not self.subscribed or len(p)!=2 or not all(isinstance(x,str) for x in p) or self.worker:await self.reply(id,False);continue
      address=await self.pool.auth(p[0],p[1])
      if not address:await self.reply(id,False);break
      self.worker,self.token=p;await self.reply(id,True);await self.new_job()
     elif method=='mining.submit':await self.submit(id,p)
     else:await self.reply(id,error=[20,'Unsupported method',None])
    except (ValueError,TypeError,KeyError,AttributeError):await self.reply(None,error=[20,'Malformed request',None])
  except (asyncio.TimeoutError,ConnectionError,ValueError):pass
  except Exception as e:LOG.warning('Client closed (%s)',type(e).__name__)
 async def submit(self,id,p):
  if not self.worker:return await self.reply(id,error=[24,'Authorize first',None])
  if len(p)!=5 or not all(isinstance(x,str) for x in p) or p[0]!=self.worker:return await self.reply(id,error=[20,'Invalid submit',None])
  _,jobid,e2,nt,nonce=p;j=self.jobs.get(jobid)
  if not j or time.time()-j.created>60:return await self.reply(id,error=[21,'Stale job',None])
  if any(not re.fullmatch('[a-fA-F0-9]{8}',s) for s in [e2,nt,nonce]):return await self.reply(id,error=[20,'Invalid hex',None])
  if int(nt,16)!=j.t['curtime']:return await self.reply(id,error=[20,'Time rolling unsupported; use job time',None])
  if time.time()-self.auth_at>15:
   if await self.pool.auth(self.worker,self.token)!=self.address:self.writer.close();return
   self.auth_at=time.time()
  if await self.pool.rpc('getbestblockhash')!=j.t['previousblockhash']:return await self.reply(id,error=[21,'Stale tip',None])
  key=(e2.lower(),nt.lower(),nonce.lower())
  if key in j.seen:return await self.reply(id,error=[22,'Duplicate share',None])
  if len(j.seen)>=1000:self.writer.close();return
  j.seen.add(key);h,block=j.candidate(self.extra,e2,nt,nonce)
  if int.from_bytes(h,'little')>target(j.t['bits']):return await self.reply(id,error=[23,'Low difficulty share',None])
  bh=h[::-1].hex()
  if self.pool.db.execute('select 1 from shares where hash=?',(bh,)).fetchone():return await self.reply(id,error=[22,'Duplicate share',None])
  self.pool.db.execute('insert into shares values(?,?,?,?,?)',(bh,self.worker,j.t['height'],'pending',int(time.time())));self.pool.db.commit()
  result=await self.pool.rpc('submitblock',block.hex())
  accepted=result is None
  self.pool.metrics.proof(self.worker,bh,target(j.t['bits']))
  self.pool.db.execute('update shares set status=? where hash=?',('accepted' if accepted else 'rejected:'+str(result),bh));self.pool.db.commit()
  self.pool.metrics.emit(self.pool.clients,self.pool.template,GENESIS)
  LOG.info('Block %s height=%d status=%s',bh,j.t['height'],'accepted' if accepted else result)
  await self.reply(id,True if accepted else None,None if accepted else [20,'Block rejected: '+str(result),None])
  if accepted:
   await self.pool.refresh()
   for c in list(self.pool.clients):
    if c.worker:
     try:await c.new_job()
     except Exception:c.writer.close()
def main():
 global WORKERS
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workers',required=True,help='Local hashed device credentials, Mainnet local credential registry; web registration integration is separate');p.add_argument('--data-dir',default='/var/lib/azmon-mainnet');p.add_argument('--rpc-port',type=int,default=29754);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=3333);p.add_argument('--journal',default='azmon-shares.sqlite');p.add_argument('--tls-cert');p.add_argument('--tls-key');p.add_argument('--allow-lan-plaintext',action='store_true');a=p.parse_args()
 WORKERS=a.workers
 if os.stat(WORKERS).st_mode & 0o007:p.error("Worker file must not be world-readable")
 tls=None
 if a.tls_cert and a.tls_key:tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(a.tls_cert,a.tls_key)
 if a.host not in ('127.0.0.1','::1') and not tls and not a.allow_lan_plaintext:p.error('Non-loopback requires TLS or explicit --allow-lan-plaintext for trusted LAN tests only')
 logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
 cookie=pathlib.Path(a.data_dir).expanduser()/'azmon-mainnet'/'.cookie'
 try:asyncio.run(Pool(RPC(cookie,a.rpc_port),a.journal).run(a.host,a.port,tls))
 except KeyboardInterrupt:pass
if __name__=='__main__':main()
