#!/usr/bin/env python3
"""Independent source identity checks; never infer a deployment from source."""
import hashlib,json,pathlib,re,struct
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 m=json.loads((ROOT/'release.json').read_text());g=json.loads((ROOT/'genesis.json').read_text())
 header=bytes.fromhex(g['headerHex']);tx=bytes.fromhex(g['transactionHex'])
 double=lambda b:hashlib.sha256(hashlib.sha256(b).digest()).digest()
 assert len(header)==80 and header[4:36]==bytes(32)
 assert double(header)[::-1].hex()==g['hash']
 assert double(tx)==header[36:68] and double(tx)[::-1].hex()==g['merkle']
 _,_,bits,nonce=struct.unpack('<IIII',header[64:80]);assert bits==int(g['bits'],16) and nonce==g['nonce']
 target=(bits&0x7fffff)<<(8*((bits>>24)-3))
 assert int.from_bytes(double(header),'little')<=target
 # Parse the single genesis input/output, not just the accompanying JSON.
 assert tx[:5]==bytes.fromhex('0100000001') and tx[5:37]==bytes(32) and tx[37:41]==bytes.fromhex('ffffffff')
 script_length=tx[41];offset=42+script_length
 assert tx[offset:offset+5]==bytes.fromhex('ffffffff01')
 assert tx[offset+5:offset+13]==bytes(8) and tx[offset+13:]==bytes.fromhex('016a00000000')
 assert g['hash'] not in ['0000bf0f94f19fceff8b53bb1bbc53bf1aafd39b03cc2c5248b58c329b486884','0000cc1c8e4f0cde0a92d40091794d6ac9b295bc802837716adaed27afe67a72']
 core=(ROOT/'core/src/kernel/chainparams.cpp').read_text();main=core[core.index('class CMainParams :'):core.index('class CTestNetParams :')]
 assert g['hash'] in main and g['merkle'] in main and f'0x{g["bits"]}' in main
 assert f'{target:064x}' in main and 'nDefaultPort = 29755' in main and 'pchMessageStart[3] = 0x4e' in main
 assert 'fPowAllowMinDifficultyBlocks = false' in main and 'fPowNoRetargeting = false' in main
 assert 'nSubsidyHalvingInterval = 210000' in main and '10 * 60' in main
 for relative in ['stratum/server.py','scripts/wallet_tool.py']:
  text=(ROOT/relative).read_text();assert 'azmon-mainnet' in text and 'azmon-rc1' not in text
 assert g['hash'] in (ROOT/'stratum/server.py').read_text()
 assert m['publicLaunchPerformed'] is False and m['stage']=='MAINNET_PRELAUNCH_VALIDATION'
 print(json.dumps({'status':'PASS','scope':'Source/genesis identity only; not deployment approval','genesis':g['hash'],'bits':g['bits'],'genesisReward':0,'stage':m['stage'],'publicLaunchPerformed':False},indent=2))
if __name__=='__main__':main()
