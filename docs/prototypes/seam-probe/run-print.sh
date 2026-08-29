#!/usr/bin/env bash
# Probe print mode. It runs one prompt with the fixture hook and a clean environment.
set -u
SEAM_DIR="$(cd "$(dirname "$0")" && pwd)"
"$SEAM_DIR/settings.sh"
rm -f "$SEAM_DIR/payloads.jsonl" "$SEAM_DIR/hookenv.txt"
env -u CLAUDE_CODE_ENTRYPOINT \
    -u CLAUDECODE \
    -u CLAUDE_CODE_CHILD_SESSION \
    -u CLAUDE_CODE_SESSION_ID \
    SEAM_DIR="$SEAM_DIR" \
    SEAM_MODE="${SEAM_MODE:-append}" \
    claude -p "$1" \
      --settings "$SEAM_DIR/settings.json" \
      --output-format text \
      --model haiku \
      --allowedTools Bash
