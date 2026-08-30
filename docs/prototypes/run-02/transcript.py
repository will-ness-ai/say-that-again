"""The tail of the live conversation, read from the harness transcript.

The hook payload carries `transcript_path`, a JSONL file with one record per turn. This module
turns the end of that file into the entries that `pipeline.context_block` formats.

What the file holds, and what this takes from it:

    type "user"      content is a string, or a list holding text blocks   -> a real user turn
    type "user"      content is a list holding tool_result blocks         -> what a tool returned
    type "assistant" content is a list holding text blocks                -> what the reader saw
    type "assistant" content is a list holding tool_use blocks            -> what the agent ran
    type "assistant" content is a list holding thinking blocks            -> skipped
    every other type                                                      -> skipped

A tool call and its result are joined by `tool_use_id`. Both halves are kept, because what the
agent ran and got back is often the only place a name in the answer was ever defined.

Every failure returns an empty list. A translation with no context is still correct, and no
reading of a transcript is worth losing the answer over.
"""

import json
import os

# The field of a tool input that says what the call was about, most telling first.
TELLING = ("command", "file_path", "path", "pattern", "query", "url", "skill", "prompt")


def text_of(content):
    """The plain text of a message. Thinking is not conversation the reader saw."""
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts = [b.get("text") or "" for b in content
             if isinstance(b, dict) and b.get("type") == "text"]
    return "\n".join(parts).strip()


def input_of(block):
    """The telling part of a tool input, else the whole input."""
    sent = block.get("input")
    if not isinstance(sent, dict):
        return str(sent or "")
    for field in TELLING:
        if sent.get(field):
            return str(sent[field])
    return json.dumps(sent)


def result_of(block):
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text") or "" for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(parts) or json.dumps(content)
    return json.dumps(content or "")


def records(path):
    for line in open(path, errors="replace"):
        try:
            record = json.loads(line)
        except Exception:
            continue
        if record.get("isMeta") or record.get("isSidechain"):
            continue
        if record.get("type") in ("user", "assistant"):
            yield record


def tail(payload, exchanges=5):
    """The last `exchanges` user turns and everything that followed each, oldest first."""
    path = (payload or {}).get("transcript_path") or ""
    if not path or not os.path.exists(path):
        return []

    try:
        every = list(records(path))
    except Exception:
        return []

    entries = []
    results = {}
    for record in every:
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        blocks = content if isinstance(content, list) else []

        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                results[block.get("tool_use_id")] = (result_of(block),
                                                     bool(block.get("is_error")))

        said = text_of(content)
        if said:
            entries.append((record.get("type"), said))
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                entries.append(("tool", block.get("name") or "tool",
                                input_of(block), block.get("id")))

    filled = []
    for entry in entries:
        if entry[0] == "tool":
            back, failed = results.get(entry[3], ("", False))
            filled.append(("tool", entry[1], entry[2], back, failed))
        else:
            filled.append(entry)

    starts = [i for i, e in enumerate(filled) if e[0] == "user"]
    if len(starts) > exchanges:
        filled = filled[starts[-exchanges]:]
    return filled
