#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run on mainnet preparation VPS as root'; exit 1; }
root=/opt/azmon-mainnet
cli=(runuser -u azmonmain -- /usr/local/lib/azmon-mainnet/bitcoin-cli -datadir=/var/lib/azmon-mainnet -chain=main -rpcwait)
if ! "${cli[@]}" -rpcwallet=azmon-wallet getwalletinfo >/dev/null 2>&1; then
 if ! "${cli[@]}" loadwallet azmon-wallet true >/dev/null 2>&1; then
  "${cli[@]}" -named createwallet wallet_name=azmon-wallet load_on_startup=true
 fi
fi
address="$("${cli[@]}" -rpcwallet=azmon-wallet getnewaddress mining bech32)"
runuser -u azmonmain -- python3 "$root/stratum/create_worker.py" --file /var/lib/azmon-mainnet/workers.json --address "$address"
cat > /etc/systemd/system/azmon-mainnet-stratum.service <<'UNIT'
[Unit]
Description=AZMON Mainnet SOLO; loopback only
Requires=azmon-mainnet-node.service
After=azmon-mainnet-node.service azmon-mainnet-peer.service
[Service]
User=azmonmain
Group=azmonmain
ExecStart=/usr/bin/python3 /opt/azmon-mainnet/stratum/server.py --data-dir /var/lib/azmon-mainnet --rpc-port 29754 --host 127.0.0.1 --port 3373 --journal /var/lib/azmon-mainnet/shares.sqlite --workers /var/lib/azmon-mainnet/workers.json
Restart=on-failure
RestartSec=10
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=/var/lib/azmon-mainnet
[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/systemd/system/azmon-mainnet-explorer.service <<'UNIT'
[Unit]
Description=AZMON Mainnet read-only explorer
Requires=azmon-mainnet-node.service
After=azmon-mainnet-node.service
[Service]
User=azmonmain
Group=azmonmain
ExecStart=/usr/bin/python3 /opt/azmon-mainnet/explorer/server.py --data-dir /var/lib/azmon-mainnet --rpc-port 29754 --port 29980
Restart=on-failure
RestartSec=10
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now azmon-mainnet-stratum azmon-mainnet-explorer
printf 'AZMON payout address: %s\n' "$address"
echo 'Copy the device credential locally. Do not post it in chat. No DNS or firewall changes made.'
