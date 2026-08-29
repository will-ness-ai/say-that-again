# Seam probe

A fixture that tests the `MessageDisplay` seam against a running harness. It answers the questions [ADR 0006](../../adr/0006-attach-at-messagedisplay-and-append-to-the-final-delta.md) decides, and the results are in [`docs/research/seam-measurements.md`](../../research/seam-measurements.md).

The fixture makes no model call of its own. It logs what the seam gives it, then returns a fixed marker in place of a translation. That keeps each probe fast and makes the result unambiguous: the marker is on screen, or it is not.

## Files

| File | Job |
|---|---|
| `hook.sh` | The `MessageDisplay` hook. Logs the delta and the environment, then calls `reply.py`. |
| `reply.py` | Answers the final delta. `SEAM_MODE` selects append, crash, or garbage. |
| `settings.sh` | Writes `settings.json` with an absolute hook path. |
| `run-print.sh` | Runs one prompt through `claude -p`. |
| `run-tty.sh` | Runs one prompt through a real terminal, using `tmux`. |

`settings.json`, `payloads.jsonl`, `hookenv.txt`, `pane.txt` and `work/` are generated. They are not committed, because the paths inside them name a machine.

## Run

```sh
docs/prototypes/seam-probe/run-print.sh "Say exactly: hello world"
docs/prototypes/seam-probe/run-tty.sh "Write four short lines about the sea. No preamble."
SEAM_MODE=crash docs/prototypes/seam-probe/run-tty.sh "Write four short lines about rain."
docs/prototypes/seam-probe/run-tty.sh "Write four short lines about the sea." --verbose
```

`run-tty.sh` needs `tmux`. It accepts the workspace trust dialog for you on a first run.

## Read the result

The pane that `run-tty.sh` prints shows what the reader would see. `[[APPENDED-TRANSLATION]]` stands where a translation would go.

To see the cadence the seam offered:

```sh
python3 -c "
import json
for line in open('docs/prototypes/seam-probe/payloads.jsonl'):
    d = json.loads(line)
    print(d['message_id'][:8], d['index'], d['final'], repr(d['delta'])[:60])
"
```
