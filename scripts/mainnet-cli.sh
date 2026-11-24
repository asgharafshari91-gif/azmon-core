#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
exec "${AZMON_BIN_DIR:-$root/build/bin}/bitcoin-cli" -chain=main -datadir="${AZMON_DATA_DIR:-$root/mainnet-data}" "$@"
