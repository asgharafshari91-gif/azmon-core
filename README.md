# AZMON Core 0.3.0

AZMON is a Bitcoin Core-based SHA-256d proof-of-work chain with an independent genesis. Core source and build/test scripts are published for inspection. This repository is not an exchange endorsement or an independent security audit.

- Website: https://azmon.lister.com.tr
- Explorer: https://azmon.lister.com.tr/explorer
- Protocol facts: https://azmon.lister.com.tr/project
- Genesis: `000000057eacbad83bbf08d90a98403e0bcfc5bd8566fb9d92962786096d274c`
- Initial block subsidy: 250 AZMON; halvings every 210,000 blocks; 8 decimal places.
- Coinbase maturity: 100 additional blocks. Supply ceiling: 105 million AZMON.
- P2P bootstrap: `2.31.168.110:29755`; TLS SOLO mining: `pool.azmon.lister.com.tr:3444`.

## Build

On Ubuntu, install build-essential, cmake, pkg-config, libboost-dev, libevent-dev and libsqlite3-dev. Then run `AZMON_JOBS=2 bash scripts/build.sh`. The resulting binaries retain the upstream names `build/bin/bitcoind` and `build/bin/bitcoin-cli`.

`python3 scripts/check_release.py` checks source/genesis identity only. `python3 scripts/test_chain.py --build build` uses temporary isolated nodes and proof-of-work solving; it can take time. Read the script and its limitations before running. Historical prelaunch labels in the original release package do not describe current network state.

## Security and custody

Private keys and signing belong in the user's local wallet, not a website. Do not expose JSON-RPC publicly. Report reproducible vulnerabilities privately to proje@lister.com.tr. No guaranteed response time, independent audit or bug-bounty payment is promised.

## Status

Linux and macOS builds and an actual mainnet transfer have been exercised. Native Windows Core binaries and physical ASIC compatibility have not been certified. The project-operated services are not evidence of independently distributed infrastructure. No exchange listing or guaranteed market value is claimed.

## Provenance and license

Imported from the published AZMON-Mainnet-0.3.0.zip with SHA-256 `0a3c118f0df5c4fd85bdd76afe26359716437c9a24e84eacbca6c1bac62ca6ea`. Preserve the Bitcoin Core copyright notices and MIT license in `core/COPYING` and source files. Original release notes remain in this repository.
