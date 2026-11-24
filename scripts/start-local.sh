#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
data="${AZMON_DATA_DIR:-$root/mainnet-data}"
umask 077
mkdir -p "$data"
if [[ ! -e "$data/bitcoin.conf" ]]; then
cat > "$data/bitcoin.conf" <<'CONF'
chain=main
server=1
dnsseed=0
fixedseeds=0
discover=0
listenonion=0
fallbackfee=0.0001
[main]
bind=127.0.0.1:29755
rpcbind=127.0.0.1
rpcallowip=127.0.0.1
rpcport=29754
CONF
fi
exec "${AZMON_BIN_DIR:-$root/build/bin}/bitcoind" -datadir="$data" -printtoconsole=1
