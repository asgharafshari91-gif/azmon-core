#!/usr/bin/env python3
import asyncio,hashlib,json,pathlib,secrets,sys,tempfile
root=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'stratum'));import server
worker='00000000-0000-0000-0000-000000000123';token=secrets.token_hex(32)
async def test():
 with tempfile.TemporaryDirectory() as d:
  p=pathlib.Path(d)/'workers.json';server.WORKERS=str(p)
  assert await server.authorize(worker,token) is None
  row={'enabled':True,'tokenHash':hashlib.sha256(token.encode()).hexdigest(),'address':'az1fixture'};p.write_text(json.dumps({worker:row}));p.chmod(0o600)
  assert token not in p.read_text()
  assert await server.authorize(worker,token)=='az1fixture'
  assert await server.authorize(worker,'b'*64) is None
  row['enabled']=False;p.write_text(json.dumps({worker:row}));assert await server.authorize(worker,token) is None
  assert await server.authorize('bad-id',token) is None
  p.write_text('{broken');assert await server.authorize(worker,token) is None
  print('PASS: local hashed credential, wrong token, immediate revocation and malformed data fail closed')
asyncio.run(test())
