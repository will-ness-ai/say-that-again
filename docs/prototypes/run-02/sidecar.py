"""The sidecar, end to end, at the MessageDisplay seam.

One delta of one text block reaches one run of this program. The run buffers the delta and
exits. On the final delta the run assembles the text block, tests the gate, calls the model
two times, and answers with the original delta plus the translation below it.

Every error path prints nothing and exits 0, so the harness draws the original. See ADR 0006.

Environment:
  STA_DIR      the directory of this prototype (set by hook.sh)
  STA_STATE    where the delta buffer and the log go
  STA_STYLE    style name or path, default `plain`
  STA_MODEL    model id, default anthropic/claude-haiku-4.5
  STA_DETECT   `on` to stand down when a discard mode is found, default `off`
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import discard  # noqa: E402
import pipeline  # noqa: E402

SEPARATOR = "───────────── say that again ─────────────"
STATE = os.environ.get("STA_STATE") or os.path.join(HERE, "state")


def log(record):
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(os.path.join(STATE, "log.jsonl"), "a") as handle:
            handle.write(json.dumps(record) + "\n")
    except Exception:
        pass


def buffer_path(message_id):
    safe = "".join(c for c in message_id if c.isalnum() or c in "-_")[:64]
    return os.path.join(STATE, f"block-{safe}.txt")


def answer(text):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "MessageDisplay",
            "displayContent": text,
        }
    }))


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except Exception:
        return
    os.makedirs(STATE, exist_ok=True)

    # P4 and P6: in print mode this hook replaces the program's answer, not the display.
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT") != "cli":
        log({"at": time.time(), "event": "stand down", "why": "entrypoint",
             "entrypoint": os.environ.get("CLAUDE_CODE_ENTRYPOINT")})
        return

    message_id = payload.get("message_id") or "unknown"
    delta = payload.get("delta") or ""
    path = buffer_path(message_id)
    with open(path, "a") as handle:
        handle.write(delta)

    if not payload.get("final"):
        return

    text_block = open(path).read()
    os.remove(path)

    seen = discard.inspect(payload)
    record = {
        "at": time.time(), "message_id": message_id, "chars": len(text_block),
        "deltas": payload.get("index", 0) + 1, "discard": seen,
    }

    if not pipeline.passes_gate(text_block):
        record["event"] = "gate"
        log(record)
        return

    if os.environ.get("STA_DETECT") == "on" and seen["verdict"] != "clear":
        record["event"] = "stand down"
        record["why"] = seen["verdict"]
        log(record)
        return

    try:
        style = pipeline.load_style(os.environ.get("STA_STYLE") or "plain")
        model = os.environ.get("STA_MODEL") or pipeline.DEFAULT_MODEL
        result = pipeline.run(text_block, style, model)
    except pipeline.CallFailure as failure:
        record["event"] = "fail-open"
        record["failure"] = failure.cls
        log(record)
        return
    except Exception as error:
        record["event"] = "fail-open"
        record["failure"] = f"unexpected: {error}"
        log(record)
        return

    record["event"] = "translated"
    record["result"] = {k: v for k, v in result.items() if k != "translation"}
    record["translation"] = result["translation"]
    record["original"] = text_block
    log(record)

    if not result["translation"]:
        return
    answer(f"{delta}\n\n{SEPARATOR}\n\n{result['translation']}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
