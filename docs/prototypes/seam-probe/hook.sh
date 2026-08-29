#!/usr/bin/env bash
# A MessageDisplay fixture. It logs every delta, then answers only the final one.
in=$(cat)
printf '%s\n' "$in" >> "$SEAM_DIR/payloads.jsonl"
{
  printf 'ENTRYPOINT=%s ' "${CLAUDE_CODE_ENTRYPOINT:-<unset>}"
  printf 'CLAUDECODE=%s ' "${CLAUDECODE:-<unset>}"
  printf 'CHILD=%s ' "${CLAUDE_CODE_CHILD_SESSION:-<unset>}"
  printf 'TERM=%s\n' "${TERM:-<unset>}"
} >> "$SEAM_DIR/hookenv.txt"
printf '%s' "$in" | python3 "$SEAM_DIR/reply.py"
