#!/usr/bin/env bash
# Write settings.json with an absolute hook path. The file is generated, never committed,
# because the path names a machine.
#
# STA_SETTINGS_EXTRA holds a JSON object that is merged into the file at run time. A probe
# that must switch a plugin off passes the plugin name that way, so no machine detail and no
# third-party name lands in this repository.
set -u
STA_DIR="$(cd "$(dirname "$0")" && pwd)"
STA_DIR="$STA_DIR" STA_SETTINGS_EXTRA="${STA_SETTINGS_EXTRA:-{\}}" python3 - <<'PY'
import json, os

directory = os.environ["STA_DIR"]
settings = {
    "hooks": {
        "MessageDisplay": [
            {"hooks": [{"type": "command",
                        "command": os.path.join(directory, "hook.sh"),
                        "timeout": 120}]}
        ]
    }
}
settings.update(json.loads(os.environ["STA_SETTINGS_EXTRA"]))
json.dump(settings, open(os.path.join(directory, "settings.json"), "w"), indent=2)
PY
