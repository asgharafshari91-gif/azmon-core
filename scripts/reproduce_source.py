#!/usr/bin/env python3
"""Reproduce bundled source from the exact official archive and AZMON patch."""
import argparse,hashlib,json,pathlib,shutil,subprocess,tarfile,tempfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination',type=pathlib.Path);p.add_argument('--archive',type=pathlib.Path);a=p.parse_args()
destination=a.destination.resolve()
if destination.exists():raise SystemExit('Use a new, nonexistent destination; no source tree is overwritten.')
u=json.loads((ROOT/'UPSTREAM.json').read_text())
with tempfile.TemporaryDirectory(prefix='azmon-reproduce-') as tmp:
 temp=pathlib.Path(tmp);archive=a.archive
 if archive is None:
  archive=temp/'upstream.tar.gz'
  with urllib.request.urlopen(u['sourceURL'],timeout=60) as response:
   if not response.geturl().startswith('https://'):raise SystemExit('HTTPS required')
   with archive.open('wb') as output:shutil.copyfileobj(response,output)
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=u['sourceArchiveSHA256']:raise SystemExit('Official source archive checksum mismatch')
 with tarfile.open(archive) as tar:
  for item in tar.getmembers():
   parts=pathlib.PurePosixPath(item.name).parts
   if not parts or parts[0]!='bitcoin-30.4' or '..' in parts or not(item.isfile() or item.isdir()):raise SystemExit('Unexpected archive entry')
  tar.extractall(temp)
 source=temp/'bitcoin-30.4'
 subprocess.run(['git','-C',str(source),'apply','--check',str(ROOT/'azmon.patch')],check=True)
 subprocess.run(['git','-C',str(source),'apply',str(ROOT/'azmon.patch')],check=True)
 shutil.copytree(source,destination)
 print('AZMON source reproduced:',destination)
 print('Archive SHA-256 verified; this does not claim independent publisher PGP signature verification.')
