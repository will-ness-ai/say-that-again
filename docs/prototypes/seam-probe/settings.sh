#!/usr/bin/env bash
# Write settings.json with an absolute hook path. The file is generated, never committed,
# because the path names a machine.
set -u
SEAM_DIR="$(cd "$(dirname "$0")" && pwd)"
cat > "$SEAM_DIR/settings.json" <<EOF
{
  "hooks": {
    "MessageDisplay": [
      {
        "hooks": [
          { "type": "command", "command": "$SEAM_DIR/hook.sh", "timeout": 120 }
        ]
      }
    ]
  }
}
EOF
