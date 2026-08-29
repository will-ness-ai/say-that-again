#!/usr/bin/env bash
# The MessageDisplay hook entry. It loads the key, then runs the sidecar.
# It exits 0 on every path, because the harness draws the original when the hook says nothing.
STA_DIR="$(cd "$(dirname "$0")" && pwd)"
export STA_DIR
export STA_STATE="${STA_STATE:-$STA_DIR/state}"
python3 "$STA_DIR/sidecar.py"
exit 0
