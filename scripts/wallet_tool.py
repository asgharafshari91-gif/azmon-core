#!/usr/bin/env python3
"""Local AZMON wallet operations; secrets stay off shell history and argv."""
import argparse,base64,getpass,json,pathlib,urllib.parse,urllib.request
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data-dir',required=True);p.add_argument('--rpc-port',type=int,default=29754);p.add_argument('--wallet',default='azmon-wallet');g=p.add_mutually_exclusive_group(required=True);g.add_argument('--info',action='store_true');g.add_argument('--new-address',action='store_true');g.add_argument('--backup',metavar='ABSOLUTE_PATH');g.add_argument('--encrypt',action='store_true');a=p.parse_args()
cookie=pathlib.Path(a.data_dir)/'azmon-mainnet/.cookie'
def rpc(method,*params,wallet=True):
 auth=base64.b64encode(cookie.read_bytes().strip()).decode();url='http://127.0.0.1:%d/'%a.rpc_port
 if wallet:url+='wallet/'+urllib.parse.quote(a.wallet,safe='')
 request=urllib.request.Request(url,json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),{'Authorization':'Basic '+auth,'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=30) as r:data=json.loads(r.read(1048576))
 if data.get('error'):raise SystemExit('Wallet RPC rejected operation. Check local wallet state; no passphrase is printed.')
 return data['result']
manifest=json.loads((pathlib.Path(__file__).resolve().parents[1]/'genesis.json').read_text())
if rpc('getblockhash',0,wallet=False)!=manifest['hash']:raise SystemExit('Wrong genesis; refused')
if a.info:result=rpc('getbalances')
elif a.new_address:result=rpc('getnewaddress','mining','bech32')
elif a.backup:
 path=pathlib.Path(a.backup)
 if not path.is_absolute() or path.exists():raise SystemExit('Use a new absolute backup filename; existing files are never overwritten')
 result=rpc('backupwallet',str(path))
else:
 password=getpass.getpass('New AZMON wallet passphrase: ');again=getpass.getpass('Confirm passphrase: ')
 if len(password)<16 or password!=again:raise SystemExit('Use matching passphrases of at least 16 characters')
 result=rpc('encryptwallet',password);password=again=None
print(json.dumps(result,indent=2))
