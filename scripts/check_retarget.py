#!/usr/bin/env python3
"""Compile actual retarget function with real uint256 arithmetic and isolated index stubs."""
import json,re,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=(root/'core/src/pow.cpp').read_text()
fn=re.search(r'unsigned int CalculateNextWorkRequired\([^\n]*\)\n\{.*?\n\}',src,re.S).group()
code='''#include <arith_uint256.h>
#include <uint256.h>
#include <cassert>
#include <cstdint>
#include <iostream>
namespace Consensus { struct Params {
 bool fPowNoRetargeting=false; bool enforce_BIP94=false;
 int64_t nPowTargetTimespan=1209600;
 uint256 powLimit{"0000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"};
 int DifficultyAdjustmentInterval() const {return 2016;}
}; }
struct CBlockIndex {
 int nHeight=2015; uint32_t nBits; int64_t time;
 const CBlockIndex* first=nullptr;
 int64_t GetBlockTime() const {return time;}
 const CBlockIndex* GetAncestor(int) const {return first;}
};
'''+fn+'''
int main() {
 Consensus::Params params;
 for (uint32_t bits : {0x1f00ffffU,0x1e3fffc0U,0x1d00ffffU}) {
  for (int64_t span : {int64_t{1},int64_t{302400},int64_t{800000},int64_t{1209600},int64_t{4838400},int64_t{9000000}}) {
   CBlockIndex first{0,bits,0,nullptr};
   CBlockIndex last{2015,bits,span,&first};
   std::cout << bits << " " << span << " " << CalculateNextWorkRequired(&last,0,params) << "\\n";
  }
 }
}
'''
def compact(n):
 size=(n.bit_length()+7)//8;word=n<<(8*(3-size)) if size<=3 else n>>(8*(size-3))
 if word&0x800000:word>>=8;size+=1
 return (size<<24)|word
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp);(p/'check.cpp').write_text(code)
 # Linux/ELF verification harness; use end-to-end test_testnet.py on macOS.
 subprocess.run(['c++','-std=c++20','-O2','-ffunction-sections','-fdata-sections','-I'+str(root/'core/src'),str(p/'check.cpp'),str(root/'core/src/arith_uint256.cpp'),'-Wl,--gc-sections','-o',str(p/'check')],check=True)
 output=subprocess.check_output([str(p/'check')],text=True)
 count=0
 for row in output.splitlines():
  bits,span,actual=map(int,row.split());target=(bits&0x7fffff) << (8*((bits>>24)-3))
  expected=compact(min(int('0000'+'f'*60,16),target*max(302400,min(4838400,span))//1209600))
  assert actual==expected,(bits,span,actual,expected)
  count+=1
report={'status':'PASS','cases':count,'method':'Actual C++ CalculateNextWorkRequired and arith_uint256.cpp compiled with isolated index/parameter stubs; compared to Python arbitrary-precision integers','coverage':'Three base targets; lower/upper clamp, fractional and unchanged interval; Bitcoin-style last-block base; BIP94 disabled on RC1'}
(root/'reports/retarget-arithmetic.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
