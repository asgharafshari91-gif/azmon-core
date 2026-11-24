#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cmake -S "$root/core" -B "$root/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="" -DENABLE_IPC=OFF -DBUILD_TESTS=OFF -DBUILD_GUI=OFF -DBUILD_BENCH=OFF
cmake --build "$root/build" --target bitcoind bitcoin-cli -j "${AZMON_JOBS:-2}"
