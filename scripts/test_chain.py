#!/usr/bin/env python3
"""Real final-parameter nodes, one ephemeral block, reward and restart checks."""
import argparse,asyncio,hashlib,json,pathlib,struct,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stratum'));sys.path.insert(0,str(ROOT/'scripts'))
from server import Job,RPC,Pool
from test_utils import free_port,wait
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=pathlib.Path,default=ROOT/'build');a=p.parse_args();build=a.build.resolve()
g=json.loads((ROOT/'genesis.json').read_text());helper=ROOT/'reports/find_nonce'
subprocess.run(['c++','-std=c++20','-O3','-pthread','-I'+str(ROOT/'core/src'),str(ROOT/'scripts/find_nonce.cpp'),str(build/'lib/libbitcoin_crypto.a'),'-o',str(helper)],check=True)
ports=[free_port(),free_port()];rpcs=[free_port(),free_port()];processes={};logs={}
with tempfile.TemporaryDirectory(prefix='azmon-mainnet-validation-') as temp:
 dirs=[pathlib.Path(temp)/str(i) for i in range(2)]
 def rpc(i,method,*args):return RPC(dirs[i]/'azmon-mainnet/.cookie',rpcs[i]).call(method,*args)
 def start(i):
  logs[i]=(dirs[i]/'process.log').open('a')
  processes[i]=subprocess.Popen([str(build/'bin/bitcoind'),'-chain=main','-datadir='+str(dirs[i]),'-server=1','-dnsseed=0','-fixedseeds=0','-discover=0','-listenonion=0','-bind=127.0.0.1','-rpcbind=127.0.0.1','-rpcallowip=127.0.0.1',f'-port={ports[i]}',f'-rpcport={rpcs[i]}','-printtoconsole=0'],stdout=logs[i],stderr=logs[i])
  wait(lambda:rpc(i,'getblockhash',0)==g['hash'])
 def stop(i):
  if i not in processes:return
  try:rpc(i,'stop')
  except Exception:processes[i].terminate()
  try:processes[i].wait(timeout=30)
  except subprocess.TimeoutExpired:processes[i].kill();processes[i].wait()
  logs[i].close();del processes[i]
 try:
  for i in range(2):dirs[i].mkdir();start(i)
  rpc(0,'addnode',f'127.0.0.1:{ports[1]}','onetry');wait(lambda:rpc(0,'getconnectioncount')>=1)
  rpc(0,'createwallet','validation',False,False,'',False,True,True)
  address=rpc(0,'getnewaddress','','bech32');assert address.startswith('az1')
  assert rpc(0,'validateaddress','azt1qh2262c7qf8dr8x9umsmnzswkxv7s9x92awdc39')['isvalid'] is False
  t=rpc(0,'getblocktemplate',{'rules':['segwit']});assert t['height']==1 and t['bits']==g['bits'] and t['coinbasevalue']==25000000000
  script=bytes.fromhex(rpc(0,'validateaddress',address)['scriptPubKey'])
  job=Job(t,script);extra1=bytes.fromhex('0000000000000123');extra2='00000000'
  _,unsigned=job.candidate(extra1,extra2,f"{t['curtime']:08x}",'00000000')
  bits=int(g['bits'],16);target=(bits&0x7fffff)<<(8*((bits>>24)-3))
  print('Solving one ephemeral block at the exact final starting target; this can take several minutes.',flush=True)
  nonce=int(subprocess.check_output([str(helper),unsigned[:76].hex(),f'{target:064x}'],text=True,timeout=900))
  bh,block=job.candidate(extra1,extra2,f"{t['curtime']:08x}",f'{nonce:08x}')
  assert int.from_bytes(hashlib.sha256(hashlib.sha256(block[:80]).digest()).digest(),'little')<=target
  assert rpc(0,'submitblock',block.hex()) is None
  expected=bh[::-1].hex();wait(lambda:rpc(1,'getbestblockhash')==expected,timeout=90)
  confirmed=rpc(0,'getblock',expected,2)
  assert confirmed['height']==1 and confirmed['bits']==g['bits']
  assert confirmed['tx'][0]['vout'][0]['value']==250 and confirmed['tx'][0]['vout'][0]['scriptPubKey']['address']==address
  assert rpc(0,'getbalances')['mine']['immature']==250
  for i in range(2):stop(i)
  for i in range(2):start(i)
  if 'validation' not in rpc(0,'listwallets'):rpc(0,'loadwallet','validation')
  assert rpc(0,'getbalances')['mine']['immature']==250
  assert all(rpc(i,'getbestblockhash')==expected for i in range(2))
  rpc(0,'addnode',f'127.0.0.1:{ports[1]}','onetry')
  async def test_cpu():
   worker='00000000-0000-0000-0000-000000000123';token='a'*64
   async def authorize(w,t):return address if w==worker and t==token else None
   pool=Pool(RPC(dirs[0]/'azmon-mainnet/.cookie',rpcs[0]),str(dirs[0]/'shares.sqlite'),authorize)
   await pool.refresh();server=await asyncio.start_server(pool.connect,'127.0.0.1',0,limit=16384)
   polling=asyncio.create_task(pool.poll())
   try:
    client=await asyncio.create_subprocess_exec(sys.executable,str(ROOT/'stratum/cpu_miner.py'),'--port',str(server.sockets[0].getsockname()[1]),'--seconds','70',stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,start_new_session=True)
    output,errors=await asyncio.wait_for(client.communicate((worker+'\n'+token+'\n').encode()),100)
    assert client.returncode==0,(output,errors)
    assert b'Authorized.' in output and b'Completed.' in output and b'Measured H/s:' in output
    return output.decode().strip().splitlines()[-1]
   finally:
    polling.cancel();await asyncio.gather(polling,return_exceptions=True)
    server.close();await server.wait_closed()
    for connection in list(pool.clients):connection.writer.close()
    await asyncio.sleep(.1);pool.db.close()
  print('Checking native CPU authentication, job refresh, heartbeat and clean 70-second exit...',flush=True)
  cpu_result=asyncio.run(test_cpu())
  wait(lambda:rpc(1,'getbestblockhash')==rpc(0,'getbestblockhash'),timeout=30)
  report={'status':'PASS','scope':'Actual final-genesis mainnet parameters in temporary isolated directories','checks':['Two native nodes use the distinct final genesis without RC opt-in','First block template has final initial bits and 250 AZMON reward','Actual SHA-256d block at final target accepted; peer synchronizes','Coinbase pays the generated az1 wallet; reward is immature','Both nodes restarted; chain tip and wallet reward persist'],'genesis':g['hash'],'initialBits':g['bits'],'ephemeralHeight':1,'publicBlocksMined':0,'limitations':['One block only; full 2016-block final-difficulty run not performed','Funded transfer, maturity and retarget were tested on RC1 separately; historical RC1 checks are not new release results','Local Linux x86_64 only; this release still requires VPS and native Mac checks','No public deployment or independent security audit']}
  report['checks'].append('Native CPU client authorizes, receives refreshed work, sends heartbeat and exits cleanly after 70 seconds')
  report['cpuClientSummary']=cpu_result;report['ephemeralHeight']=rpc(0,'getblockcount')
  (ROOT/'reports/mainnet-smoke.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 finally:
  for i in list(processes):stop(i)
