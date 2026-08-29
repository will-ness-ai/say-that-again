#!/usr/bin/env bash
# Probe an interactive terminal. It drives the harness through tmux and reads the pane back.
# Usage: run-tty.sh "<prompt>" [extra harness flags]
set -u
SEAM_DIR="$(cd "$(dirname "$0")" && pwd)"
SESSION="seam$$"
PROMPT="$1"
EXTRA="${2:-}"
"$SEAM_DIR/settings.sh"
rm -f "$SEAM_DIR/payloads.jsonl" "$SEAM_DIR/hookenv.txt"
mkdir -p "$SEAM_DIR/work"

tmux kill-session -t "$SESSION" 2>/dev/null
tmux new-session -d -s "$SESSION" -x 100 -y 45 -c "$SEAM_DIR/work" "bash -l"
tmux send-keys -t "$SESSION" "export SEAM_DIR=$SEAM_DIR SEAM_MODE=${SEAM_MODE:-append}" Enter
tmux send-keys -t "$SESSION" "claude --settings $SEAM_DIR/settings.json --model haiku $EXTRA" Enter
sleep 15

# Accept the workspace trust dialog on a first run in this directory.
tmux send-keys -t "$SESSION" Down
sleep 1
tmux send-keys -t "$SESSION" Enter
sleep 12

tmux send-keys -t "$SESSION" "$PROMPT"
sleep 3
tmux send-keys -t "$SESSION" Enter
sleep 50

tmux capture-pane -p -t "$SESSION" > "$SEAM_DIR/pane.txt"
tmux kill-session -t "$SESSION" 2>/dev/null
cat "$SEAM_DIR/pane.txt"
