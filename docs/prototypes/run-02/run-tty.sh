#!/usr/bin/env bash
# Run the sidecar against a live harness in a real terminal, through tmux.
# Usage: run-tty.sh "<prompt>" [extra harness flags]
#   STA_TAG    names the run. State goes to state/<tag>, the pane to panes/<tag>.txt.
#   STA_STYLE, STA_MODEL, STA_DETECT are passed through to the hook.
#   STA_SETTINGS_EXTRA is merged into settings.json. See settings.sh.
#   WAIT sets how long to wait after the prompt (default 90).
set -u
STA_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION="sta$$"
PROMPT="$1"
EXTRA="${2:-}"
WAIT="${WAIT:-90}"
TAG="${STA_TAG:-run}"
STATE="$STA_DIR/state/$TAG"
"$STA_DIR/settings.sh"
rm -rf "$STATE"
mkdir -p "$STATE" "$STA_DIR/panes" "$STA_DIR/work"

tmux kill-session -t "$SESSION" 2>/dev/null
tmux new-session -d -s "$SESSION" -x 100 -y 200 -c "$STA_DIR/work" "bash -l"
tmux send-keys -t "$SESSION" "export STA_STATE=$STATE STA_STYLE=${STA_STYLE:-plain} STA_MODEL=${STA_MODEL:-anthropic/claude-haiku-4.5} STA_DETECT=${STA_DETECT:-off}" Enter
tmux send-keys -t "$SESSION" "claude --settings $STA_DIR/settings.json --model haiku $EXTRA" Enter
sleep 15

# Accept the workspace trust dialog on a first run in this directory.
tmux send-keys -t "$SESSION" Down
sleep 1
tmux send-keys -t "$SESSION" Enter
sleep 12

tmux send-keys -t "$SESSION" "$PROMPT"
sleep 3
tmux send-keys -t "$SESSION" Enter
sleep "$WAIT"

# STA_PROMPT2 sends a second turn, to test a reply that has no meaning on its own.
if [ -n "${STA_PROMPT2:-}" ]; then
  tmux send-keys -t "$SESSION" "$STA_PROMPT2"
  sleep 3
  tmux send-keys -t "$SESSION" Enter
  sleep "$WAIT"
fi

tmux capture-pane -p -S -300 -t "$SESSION" > "$STA_DIR/panes/$TAG.txt"
tmux kill-session -t "$SESSION" 2>/dev/null
cat "$STA_DIR/panes/$TAG.txt"
