# AZMON 0.3.0 — Mainnet source release

This package prepares a distinct mainnet genesis and CPU-calibrated starting target. It does **not** certify or perform a public launch. Deployment stage: `MAINNET_PRELAUNCH_VALIDATION`. Do not relabel the existing development network as a launched mainnet.

## Protocol

SHA-256d; 105,000,000 AZMON money ceiling; initial reward 250 AZMON; 8 decimals; 210,000-block halvings; 100-block coinbase maturity; 600-second target; 2016-block difficulty adjustment with quarter/fourfold clamp and no minimum-difficulty exception. Zero genesis reward and no founder allocation. Maximum scheduled issuance from height 1: 104,999,749.96850000 AZMON.

Genesis: `000000057eacbad83bbf08d90a98403e0bcfc5bd8566fb9d92962786096d274c`.
Initial bits: `1d05e0a5`; initial difficulty approximately 0.1701372573. The target uses a single Mac's raw SHA benchmark (1,217,906 H/s). Actual miner throughput and participation vary; ten minutes is an average target, not a per-block guarantee. SHA-256 ASICs are not excluded. A small CPU bootstrap does not provide Bitcoin-level security; abrupt hash entry/exit can disrupt the 2016-block adjustment period.

P2P 29755, local RPC 29754, message magic `a75a4d4e`, data subdirectory `azmon-mainnet`, address HRP `az`. RC1 and testnet balances never migrate. Although RC1 also used `az1` address syntax, create separate mainnet wallets and credentials.

## Provenance

Based on Bitcoin Core **30.4** with AZMON changes in `azmon.patch`. Official HTTPS source archive checksum was verified; publisher PGP signatures were not independently verified here. See `UPSTREAM.json`. The AZMON package version is 0.3.0; the underlying client reports upstream core version 30.4.0. All upstream attribution and licenses remain included.

## Build and verify

Use a new directory. On Ubuntu 24.04, install CMake, a C++ compiler, pkg-config, Boost, libevent and SQLite development libraries first. Existing RC1 VPS dependencies already supply these.

```bash
sha256sum -c SHA256SUMS
AZMON_JOBS=1 bash scripts/build.sh
python3 scripts/check_release.py
python3 scripts/check_consensus.py
python3 scripts/check_retarget.py
python3 scripts/check_transition.py
python3 scripts/test_worker_auth.py
python3 scripts/test_client_io.py
setsid --wait python3 scripts/test_chain.py --build build </dev/null
```

`setsid` is Linux-specific. The final test creates two actual nodes in temporary directories, solves one block at the exact launch target, checks the payout and immature reward, restarts both nodes, then exercises the packaged CPU client for 70 seconds. Nonce solving may take several minutes. Temporary blocks are never broadcast to the public Internet or copied to production. This does not claim a full 2016-block run, funded transfer or 100-block maturity check at the new starting target. Earlier RC1 field tests are historical evidence, not fresh results for this release. Reports explicitly state their scope.

## Private preparation on VPS

Place this package at `/opt/azmon-mainnet`, build it, then:

```bash
sudo bash ops/install-node.sh --prepare
sudo bash ops/configure-mining.sh
```

Uses user `azmonmain`, binaries `/usr/local/lib/azmon-mainnet`, data `/var/lib/azmon-mainnet` and `/var/lib/azmon-mainnet-peer`. Peer RPC/P2P: 29764/29765. Existing configs are not automatically overwritten. RPC stays on loopback. No RC1/testnet data, services, firewall or DNS are changed.

The mining setup creates a new local `azmon-wallet`, payout address and hashed device credential. Keep the once-shown device key private. Stratum prepares at 127.0.0.1:3373, read-only explorer at 127.0.0.1:29980. Services: `azmon-mainnet-node`, `azmon-mainnet-peer`, `azmon-mainnet-stratum`, `azmon-mainnet-explorer`. Local device credentials are not yet integrated with website mainnet registration. Separate source publication/launch notice, native Mac and VPS validation, Internet/TLS deployment, credential segregation and website/Explorer cutover are still required before public mining starts. Never privately premine the persistent production chain.

## Mining and custody

The packaged CPU client accepts the worker UUID and device key interactively, sends heartbeat messages and reports measured hashrate at exit. A short session may find no blocks at the new difficulty.

```bash
python3 stratum/cpu_miner.py --host 127.0.0.1 --port 3373 --seconds 120
```

Internet connections require TLS. The experimental SOLO service pays an accepted block's coinbase directly to the registered AZMON address, with fees; it maintains no custodial website balance. It has a 32-connection limit, fixed network difficulty and no VarDiff/version rolling/PPS/PPLNS. ASIC firmware, load/DDoS resilience and hardware-wallet support are not hardware-certified. Registering a device does not start a miner.

`scripts/wallet_tool.py` checks genesis before wallet operations and keeps passphrases off argv. Wallet backups contain private keys; store them outside web roots and test restoration. Offline backup does not imply Ledger/Trezor integration. No independent security audit or full upstream regression suite has been completed; no exchange listing, market price or return is guaranteed.
