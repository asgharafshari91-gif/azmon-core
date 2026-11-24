#!/usr/bin/env python3
"""Compile actual transition bounds; catch the low-difficulty uint256 overflow."""
import json,pathlib,re,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
src=(ROOT/'core/src/pow.cpp').read_text();fn=re.search(r'bool PermittedDifficultyTransition\([^\n]*\)\n\{.*?\n\}',src,re.S).group()
def compact(n):
 size=(n.bit_length()+7)//8;word=n<<(8*(3-size)) if size<=3 else n>>(8*(size-3))
 if word&0x800000:word>>=8;size+=1
 return size<<24|word
def target(bits):return (bits&0x7fffff)<<(8*((bits>>24)-3))
limit=int('0000'+'f'*60,16);cases=[]
for old in [0x1f00ffff,0x1e3fffc0,0x1d00ffff]:
 for height in [2015,2016,2017,4032]:
  for num,den in [(1,1),(1,4),(4,1),(1,16),(16,1)]:
   new=compact(min(limit,target(old)*num//den));t=target(new)
   expected=(old==new) if height%2016 else target(compact(min(limit,target(old)//4)))<=t<=target(compact(min(limit,target(old)*4)))
   cases.append((height,old,new,expected))
program='''#include <arith_uint256.h>
#include <uint256.h>
#include <cstdint>
#include <iostream>
namespace Consensus { struct Params {
 bool fPowAllowMinDifficultyBlocks=false;
 int64_t nPowTargetTimespan=1209600;
 uint256 powLimit{"0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"};
 int DifficultyAdjustmentInterval() const {return 2016;}
}; }
'''+fn+'\nint main(){Consensus::Params p;\n'+''.join(f'std::cout << PermittedDifficultyTransition(p,{h},{old}U,{new}U) << "\\n";\n' for h,old,new,_ in cases)+'}\n'
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);(p/'check.cpp').write_text(program)
 subprocess.run(['c++','-std=c++20','-O2','-ffunction-sections','-fdata-sections','-I'+str(ROOT/'core/src'),str(p/'check.cpp'),str(ROOT/'core/src/arith_uint256.cpp'),'-Wl,--gc-sections','-o',str(p/'check')],check=True)
 results=subprocess.check_output([str(p/'check')],text=True).split()
 assert len(results)==len(cases)
 for case,actual in zip(cases,results):assert bool(int(actual))==case[3],(case,actual)
report={'status':'PASS','cases':len(cases),'method':'Actual C++ PermittedDifficultyTransition compiled with real arith_uint256; Python arbitrary-precision reference','checks':['Low bootstrap targets that overflow direct uint256 multiplication','Epoch boundary quarter/fourfold limits','Outside-boundary difficulty unchanged','Out-of-range transitions rejected']}
(ROOT/'reports/difficulty-transition.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
