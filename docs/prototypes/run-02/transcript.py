"""The tail of the live conversation, read from the harness transcript.

The hook payload carries `transcript_path`, a JSONL file with one record per turn. This module
turns the end of that file into the (role, text) pairs that `pipeline.context_block` formats.

Every failure returns an empty list. A translation with no context is still correct, and no
reading of a transcript is worth losing the answer over.
"""

import json
import os

WANTED = ("user", "assistant")


def text_of(message):
    """The plain text of one turn. Tool calls and their results are not conversation."""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "\n".join(parts).strip()


def tail(payload, turns=10):
    """The last `turns` user and assistant messages, oldest first."""
    path = (payload or {}).get("transcript_path") or ""
    if not path or not os.path.exists(path):
        return []
    try:
        lines = open(path, errors="replace").read().splitlines()
    except Exception:
        return []

    out = []
    for line in reversed(lines):
        if len(out) >= turns:
            break
        try:
            record = json.loads(line)
        except Exception:
            continue
        if record.get("isMeta") or record.get("isSidechain"):
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        role = message.get("role") or record.get("type")
        if role not in WANTED:
            continue
        text = text_of(message)
        if text:
            out.append((role, text))
    out.reverse()
    return out
