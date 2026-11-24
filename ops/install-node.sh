#!/usr/bin/env bash
# Install a distinct mainnet source release in private prelaunch mode.
set -euo pipefail
[[ ${1:-} == --prepare && $EUID == 0 ]] || { echo 'Usage: sudo bash ops/install-node.sh --prepare'; exit 1; }
root="$(cd "$(dirname "$0")/.." && pwd)"
[[ "$root" == /opt/azmon-mainnet ]] || { echo 'Use /opt/azmon-mainnet; RC1 data is never reused.'; exit 1; }
for exe in bitcoind bitcoin-cli; do [[ -x "$root/build/bin/$exe" ]] || { echo 'Build first.'; exit 1; }; done
python3 "$root/scripts/check_release.py"
for candidate in /var/lib/azmon-mainnet/bitcoin.conf /var/lib/azmon-mainnet-peer/bitcoin.conf; do
 [[ ! -e "$candidate" ]] || { echo "Existing config: $candidate; refusing a partial replacement. Use the controlled update procedure."; exit 1; }
done
getent passwd azmonmain >/dev/null || useradd --system --home-dir /var/lib/azmon-mainnet --shell /usr/sbin/nologin azmonmain
install -d -m 0755 /usr/local/lib/azmon-mainnet
install -m 0755 "$root/build/bin/bitcoind" "$root/build/bin/bitcoin-cli" /usr/local/lib/azmon-mainnet/
for slot in node peer; do
 if [[ $slot == node ]]; then data=/var/lib/azmon-mainnet; port=29755; rpc=29754; connect=''; else data=/var/lib/azmon-mainnet-peer; port=29765; rpc=29764; connect=127.0.0.1:29755; fi
 install -d -o azmonmain -g azmonmain -m 0700 "$data"
 if [[ -e "$data/bitcoin.conf" ]]; then
  echo "Existing config: $data/bitcoin.conf; refusing automatic replacement. Inspect it before updating."
  exit 1
 fi
 cat > "$data/bitcoin.conf" <<CONF
chain=main
server=1
dnsseed=0
fixedseeds=0
discover=0
listenonion=0
fallbackfee=0.0001
[main]
bind=127.0.0.1:$port
rpcbind=127.0.0.1
rpcallowip=127.0.0.1
rpcport=$rpc
CONF
 [[ -z $connect ]] || echo "connect=$connect" >> "$data/bitcoin.conf"
 chown azmonmain:azmonmain "$data/bitcoin.conf"; chmod 0600 "$data/bitcoin.conf"
 cat > "/etc/systemd/system/azmon-mainnet-$slot.service" <<UNIT
[Unit]
Description=AZMON mainnet $slot; deployment in prelaunch validation
After=network.target
[Service]
User=azmonmain
Group=azmonmain
ExecStart=/usr/local/lib/azmon-mainnet/bitcoind -datadir=$data -printtoconsole=1
Restart=on-failure
RestartSec=10
TimeoutStopSec=180
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$data
[Install]
WantedBy=multi-user.target
UNIT
done
systemctl daemon-reload
systemctl enable --now azmon-mainnet-node azmon-mainnet-peer
echo 'Mainnet genesis services started on loopback. No public mining was started; no firewall, DNS, RC1 or testnet service was changed.'
