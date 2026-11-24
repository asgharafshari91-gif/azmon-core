"""Server-only proof statistics. No miner-reported hash rates or device credentials."""
import json,os,pathlib,time,uuid
class Metrics:
 def __init__(self,db,path):
  self.db=db;self.path=pathlib.Path(path);self.boot=str(uuid.uuid4());self.sequence=0
  db.execute('create table if not exists telemetry_workers(worker text primary key,first_seen real,last_seen real,rejected integer not null default 0)')
  db.execute('create table if not exists telemetry_proofs(hash text primary key,worker text,work real,created real)')
  db.execute('create index if not exists telemetry_proofs_time on telemetry_proofs(created)');db.commit()
 def touch(self,worker,now=None):
  now=time.time() if now is None else now
  self.db.execute('insert into telemetry_workers(worker,first_seen,last_seen) values(?,?,?) on conflict(worker) do update set last_seen=excluded.last_seen',(worker,now,now));self.db.commit()
 def reject(self,worker):
  self.db.execute('update telemetry_workers set rejected=rejected+1 where worker=?',(worker,));self.db.commit()
 def proof(self,worker,bh,target,now=None):
  now=time.time() if now is None else now
  self.db.execute('insert or ignore into telemetry_proofs values(?,?,?,?)',(bh,worker,2**256/(target+1),now));self.db.commit()
 def snapshot(self,clients,template,genesis,now=None):
  now=time.time() if now is None else now
  online={}
  for c in clients:
   if c.metered and not c.writer.is_closing():online[c.worker]=online.get(c.worker,0)+1
  # Keep enough history for a full rolling 15-minute estimate, bound proof storage.
  self.db.execute('delete from telemetry_proofs where created<?',(now-900,));self.db.commit()
  rows=self.db.execute('select worker,first_seen,last_seen,rejected from telemetry_workers order by last_seen desc limit 1000').fetchall();workers=[]
  for worker,first,last,rejected in rows:
   count,work,lastshare=self.db.execute('select count(*),coalesce(sum(work),0),max(created) from telemetry_proofs where worker=? and created>=?',(worker,now-900)).fetchone()
   accepted,lastblock=self.db.execute("select count(*),max(created) from shares where worker=? and status='accepted'",(worker,)).fetchone()
   window=max(0,min(900,now-first));rate=work/window if window>=60 and count>=3 else None
   workers.append({'id':worker,'connections':online.get(worker,0),'lastSeen':int((now if online.get(worker) else last)*1000),'lastShare':int(max(x for x in [lastshare,lastblock] if x is not None)*1000) if lastshare is not None or lastblock is not None else None,'acceptedBlocks':accepted,'rejectedSubmissions':rejected,'validShares':count,'windowSeconds':window,'estimatedHashrate':rate})
  self.sequence+=1
  return {'version':1,'genesis':genesis,'bootId':self.boot,'sequence':self.sequence,'capturedAt':int(now*1000),'acceptedBlocks':self.db.execute("select count(*) from shares where status='accepted'").fetchone()[0],'nodeReady':template is not None,'height':max(0,template['height']-1) if template else 0,'workers':workers}
 def emit(self,clients,template,genesis):
  data=self.snapshot(clients,template,genesis)
  temp=self.path.with_name(self.path.name+'.tmp');fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
  with os.fdopen(fd,'w') as f:json.dump(data,f,allow_nan=False)
  os.replace(temp,self.path)
