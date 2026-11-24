#!/usr/bin/env python3
"""AZMON Mainnet miner, one CPU thread; no production ASIC claims."""
import argparse,getpass,hashlib,json,secrets,select,socket,ssl,struct,time
D=lambda b:hashlib.sha256(hashlib.sha256(b).digest()).digest()
class Wire:
 def __init__(self,s):self.s=s;self.buffer=b'';self.seq=0
 def send(self,method,params):
  self.seq+=1;self.s.sendall((json.dumps({'id':self.seq,'method':method,'params':params})+'\n').encode());return self.seq
 def read(self,timeout):
  if b'\n' not in self.buffer:
   pending=isinstance(self.s,ssl.SSLSocket) and self.s.pending()>0
   if not pending and not select.select([self.s],[],[],timeout)[0]:return None
   data=self.s.recv(16384)
   if not data:raise ConnectionError('Sunucu bağlantıyı kapattı; Stratum sunucu günlüğünü kontrol edin.')
   self.buffer+=data
   if len(self.buffer)>1048576:raise ValueError('Oversized Stratum message')
  if b'\n' not in self.buffer:return None
  line,self.buffer=self.buffer.split(b'\n',1)
  if not line.strip():return None
  return json.loads(line)
 def response(self,id,seconds=30):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   m=self.read(.2)
   if m and m.get('id')==id:return m
  raise TimeoutError('Stratum yanıtı gelmedi')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=3363);p.add_argument('--tls',action='store_true');p.add_argument('--seconds',type=int,default=120);a=p.parse_args()
 if not 1<=a.seconds<=3600:p.error('--seconds must be 1..3600')
 worker=input('AZMON Worker UUID: ').strip();token=getpass.getpass('AZMON device key: ').strip()
 s=socket.create_connection((a.host,a.port),timeout=20)
 if a.tls:s=ssl.create_default_context().wrap_socket(s,server_hostname=a.host)
 s.settimeout(20);w=Wire(s)
 try:
  sub=w.response(w.send('mining.subscribe',[]));ex1=bytes.fromhex(sub['result'][1]);size=sub['result'][2]
  auth=w.response(w.send('mining.authorize',[worker,token]));token=None
  if auth.get('result') is not True:raise ValueError('AZMON device authorization rejected')
  print('Authorized. AZMON MAINNET; Ctrl+C to stop.',flush=True)
  deadline=time.monotonic()+a.seconds;job=None;pending=None;accepted=0;rejected=0;last_ping=time.monotonic();hashes=0;started=last_ping
  while time.monotonic()<deadline:
   if time.monotonic()-last_ping>=60:
    w.send('mining.ping',[]);last_ping=time.monotonic()
   m=w.read(.05 if job is None or pending is not None else 0)
   if m:
    if m.get('method')=='mining.notify':
     jid,prev,c1,c2,branch,ver,bits,nt,_=m['params'];ex2=secrets.token_bytes(size);merkle=D(bytes.fromhex(c1)+ex1+ex2+bytes.fromhex(c2))
     for h in branch:merkle=D(merkle+bytes.fromhex(h))
     ph=bytes.fromhex(prev);ph=b''.join(ph[i:i+4][::-1] for i in range(0,32,4));b=int(bits,16);goal=(b&0x7fffff)<<(8*((b>>24)-3))
     prefix=struct.pack('<I',int(ver,16))+ph+merkle+struct.pack('<II',int(nt,16),b);job=[jid,ex2,nt,prefix,goal,0]
    elif pending is not None and m.get('id')==pending:
     if m.get('result') is True:accepted+=1;print('Accepted block:',accepted,flush=True)
     else:rejected+=1;print('Rejected:',m.get('error'),flush=True)
     pending=None
   if job is None or pending is not None:continue
   jid,ex2,nt,prefix,goal,nonce=job
   for n in range(nonce,min(nonce+2048,2**32)):
    hashes+=1
    if int.from_bytes(D(prefix+struct.pack('<I',n)),'little')<=goal:
     pending=w.send('mining.submit',[worker,jid,ex2.hex(),nt,f'{n:08x}']);job=None;break
   else:
    job[5]+=2048
    if job[5]>=2**32:job=None
  print('Completed. Accepted:',accepted,'Rejected:',rejected,'Measured H/s:',round(hashes/max(.001,time.monotonic()-started)))
 finally:s.close()
if __name__=='__main__':
 try:main()
 except KeyboardInterrupt:print('Stopped.')
 except (OSError,ValueError,KeyError,TypeError) as e:raise SystemExit(str(e))
