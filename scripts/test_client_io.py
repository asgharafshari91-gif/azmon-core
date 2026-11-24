#!/usr/bin/env python3
import importlib.util,json,pathlib,socket
root=pathlib.Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('rc_miner',root/'stratum/cpu_miner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a,b=socket.socketpair()
try:
 wire=m.Wire(a);b.sendall(b'\n{"id":1,"result":true}\n');assert wire.read(.1) is None;assert wire.read(.1)['result'] is True
 b.sendall(b'{"id":');assert wire.read(.1) is None;b.sendall(b'2}\n');assert wire.read(.1)['id']==2
 b.close()
 try:wire.read(.1);raise AssertionError('EOF was ignored')
 except ConnectionError:pass
 print('PASS: blank line, fragmented JSON, buffered line and EOF handling')
finally:a.close();b.close()
