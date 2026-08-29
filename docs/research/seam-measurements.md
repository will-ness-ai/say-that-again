# Seam measurements

Six probes that test the `MessageDisplay` seam against a running harness. They support [ADR 0006](../adr/0006-attach-at-messagedisplay-and-append-to-the-final-delta.md), and they correct two claims in [ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md).

The [attachment-point catalogue](prior-art-architecture.md) that opened this route was measured against CLI **2.1.246**, and it tells the reader to measure again on a newer build. These probes run on **2.1.251**.

| Item | Value |
|---|---|
| CLI version | 2.1.251 |
| Date | 2026-08-29 |
| Model | Haiku 4.5 |
| Fixture | [`docs/prototypes/seam-probe/`](../prototypes/seam-probe/) |

The fixture writes every payload it receives to `payloads.jsonl`, and it records four environment values. On the final delta it returns that delta's own text, then a marker line. An interactive probe runs the harness inside `tmux` and reads the pane back.

---

## P1 — The append construction works

**Prompt.** "Write four short lines about the sea. No preamble."

**On screen.**

```
⏺ Waves curl and break against the shore in endless rhythm.
  Salt air carries the calls of gulls across water and stone.
  Deep blue holds secrets in its weight and cold embrace.
  Horizon pulls the eye where sky and ocean blur as one.

  [[APPENDED-TRANSLATION]]
```

The four original lines rendered, and the marker rendered below them. The hook omitted `displayContent` on the first two deltas and answered only the last one.

**Finding.** A sidecar can append without ever holding the original. This is the construction [ADR 0006](../adr/0006-attach-at-messagedisplay-and-append-to-the-final-delta.md) selects.

## P2 — A failed translation costs nothing

**Change.** The fixture exits 1 on the final delta, and writes to stderr.

**On screen.**

```
⏺ Drops tap the window glass, a quiet rhythm.
  Earth drinks deep, thirsty after drought.
  The sky empties itself in silver threads.
  Puddles mirror clouds that gave them form.
```

All four lines rendered. No error reached the screen.

**Finding.** The fail-open contract holds on this build, and the append construction does not weaken it. A crash on the final delta costs the translation and nothing else.

## P3 — `verbose` discards the translation silently

**Change.** The harness starts with `--verbose`. The fixture is unchanged.

**On screen.** The four original lines. No marker.

**In `payloads.jsonl`.** Three fires, `index` 0 to 2, `final: true` on the last. The hook ran to completion every time.

**Finding.** The harness threw the work away and told the sidecar nothing. A real sidecar would pay for two model calls per message and deliver nothing. This is the largest open gap in the seam, and no probe closes it.

## P4 — The entrypoint separates the terminal from print mode

The fixture records `CLAUDE_CODE_ENTRYPOINT` in the hook process.

| Harness invocation | Value |
|---|---|
| Interactive terminal | `cli` |
| `claude -p` | `sdk-cli` |

**Finding.** A hook can tell the two apart before it does any work. This matters because the same hook behaves differently in the two modes — see P6.

## P5 — Prose after a tool call arrives as a new message

**Prompt.** "Say exactly: BLOCK ONE. Then run the bash command: echo hi. Then say exactly: BLOCK TWO."

**In `payloads.jsonl`.**

```
message_id 66567269…  index 0  final true  delta "BLOCK ONE"
message_id 7fe2d028…  index 0  final true  delta "BLOCK TWO"
```

**Finding.** Two fires, two `message_id` values. A tool call **ends** the assistant message, and the prose that follows opens a new one.

This dissolves the disagreement [ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md) told the seam ticket to settle. The two sources described different things, and both were right. The harness documentation says the hook fires again after a tool call — it does, for the next message. The catalogue says only the first text block of a message is offered — it is, because a message carries one.

The case that ADR 0002 used to define a text block, "prose, a tool call, then more prose in one message", does not occur.

## P6 — In print mode the hook replaces the program's answer

**Prompt.** "Say exactly: hello world", through `claude -p --output-format text`.

**On stdout.**

```
hello world

[[APPENDED-TRANSLATION]]
```

**Finding.** The seam is display-only in a terminal. In print mode it is not: the text the hook returns becomes the program's answer. A script that pipes the harness would silently receive translated text.

The sidecar must therefore stand down unless P4 proves it is in a terminal.

---

## The flush cadence

P1 and P3 both show the same shape in a terminal.

```
index 0  final false  "Waves curl and break…\nSalt air carries…\n"
index 1  final false  "Deep blue holds secrets…\n"
index 2  final true   "Horizon pulls the eye where sky and ocean blur as one."
```

The harness cuts at newlines and marks the last delta `final: true`. A sidecar collects the deltas that share a `message_id` and acts when `final` arrives.

## What these probes do not settle

- **A message that holds two text blocks.** The binary carries a render condition that hides later text blocks when a rewrite exists. No prompt in these probes produced such a message, because a tool call ends the message. The condition may be unreachable in practice. It is untested either way.
- **Whether the sidecar can learn that `verbose` is set.** P3 proves the loss. It does not find a signal.
- **Latency, and what the reader sees during the pause.** The fixture answers instantly. A real pipeline runs two model calls. That belongs to the prototype run.

## How to repeat these probes

```sh
docs/prototypes/seam-probe/run-print.sh "Say exactly: hello world"
docs/prototypes/seam-probe/run-tty.sh "Write four short lines about the sea. No preamble."
SEAM_MODE=crash docs/prototypes/seam-probe/run-tty.sh "Write four short lines about rain."
docs/prototypes/seam-probe/run-tty.sh "Write four short lines about the sea." --verbose
```

`run-tty.sh` needs `tmux`. Both scripts write `payloads.jsonl` and `hookenv.txt` beside themselves.
