#!/usr/bin/env python3
"""Compile the actual fork's subsidy function and check all issuance boundaries."""
import json, re, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
src=(ROOT/'core/src/validation.cpp').read_text()
body=re.search(r'CAmount GetBlockSubsidy\(int nHeight, const Consensus::Params& consensusParams\)\n\{.*?\n\}',src,re.S).group()
program='''#include <consensus/amount.h>
#include <cassert>
#include <iostream>
namespace Consensus { struct Params { int nSubsidyHalvingInterval = 210000; }; }
'''+body+'''
int main() {
 Consensus::Params p;
 assert(MAX_MONEY == 105000000LL * COIN);
 assert(GetBlockSubsidy(1,p)==250*COIN);
 assert(GetBlockSubsidy(209999,p)==250*COIN);
 assert(GetBlockSubsidy(210000,p)==125*COIN);
 assert(GetBlockSubsidy(420000,p)==6250000000LL);
 CAmount total=0;
 for(int era=0; era<64; ++era) {
   int h=era*210000;
   CAmount reward=GetBlockSubsidy(h,p);
   if(era) assert(reward==GetBlockSubsidy(h-1,p)/2);
   assert(GetBlockSubsidy(h+209999,p)==reward);
   total+=reward*210000;
   assert(MoneyRange(total));
 }
 assert(GetBlockSubsidy(7350000,p)==0);
 assert(GetBlockSubsidy(13440000,p)==0);
 assert(!MoneyRange(-1)); assert(!MoneyRange(MAX_MONEY+1));
 std::cout << total << " " << total-250*COIN << std::endl;
}
'''
with tempfile.TemporaryDirectory() as d:
    path=Path(d);(path/'check.cpp').write_text(program)
    subprocess.run(['c++','-std=c++20','-I'+str(ROOT/'core/src'),str(path/'check.cpp'),'-o',str(path/'check')],check=True)
    a,b=map(int,subprocess.check_output([str(path/'check')],text=True).split())
report={'status':'PASS','method':'Compile actual GetBlockSubsidy source with actual consensus/amount.h; isolated consensus parameter struct',
        'checks':'64 eras, first/last block per era, 250/125/62.5 rewards, zero reward, money bounds',
        'schedule_including_height_zero_base_units':a,'issuance_heights_1_onward_base_units':b,
        'note':'Genesis reward is zero and not spendable. Actual issuance excludes the height-zero 250-coin schedule slot. Miner underclaims and lost coins further reduce available supply.'}
(ROOT/'reports/consensus.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
