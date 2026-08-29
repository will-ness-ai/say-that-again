# Attach at `MessageDisplay`, and append to the final delta

## Status

accepted

## Decision

Say That Again attaches at the **`MessageDisplay` hook**. It appends the translation to the **final delta** of a text block. Six rules hold the decision together.

1. **One seam.** `MessageDisplay` is the only attachment point that changes assistant prose before the terminal draws it. There is no second candidate.
2. **Never blank a delta.** The sidecar omits `displayContent` on every delta but the last. On the final delta it returns that delta's own text, then a separator, then the translation. The original streams as the harness wrote it.
3. **Fail open.** Every error path exits 0 and prints nothing. The harness then draws the original. The sidecar only ever adds text; it never removes text.
4. **Stand down unless `CLAUDE_CODE_ENTRYPOINT` is `cli`.** In print mode and in the SDK the same hook replaces the program's answer on stdout. A sidecar that runs there corrupts a script.
5. **Set `timeout` to 120 seconds** in the hook entry. The default for this event is 10 seconds, and two model calls pass it.
6. **The translation is ephemeral, on purpose.** It reaches the terminal and nothing else. The transcript, the export, and the agent's own context keep the original.

## Why

**The reader wants the translation beside the answer.** Other surfaces deliver more reliably. A second terminal pane cannot be discarded by any harness setting. But the translation then sits in a window the reader is not reading, next to nothing. The value of this product is that the translation arrives where the reader already looks, so the seam that reaches that place wins even though it is the weaker channel.

**Rule 2 removes a hazard rather than managing it.** The harness offers no append. It offers replace: `displayContent` replaces the text of the delta it was given. There are two ways to build an append out of that.

| Construction | What the sidecar holds | What a fault costs |
|---|---|---|
| Blank and rebuild | The whole answer | The whole answer |
| Append to the final delta | One delta | One delta |

The prior design shipped both, and its `replace` mode is the first row. That mode blanked every delta while the message streamed, so every early exit had to reconstruct and re-emit the original. Three separate "show the original again" branches ran through one file. The second row needs none of them, because the original was never taken away.

**Rule 3 is the prior design's strongest decision, and it survived its whole history.** A dead sidecar is a safe sidecar. The measurement confirms it: a hook that exits 1 on the final delta leaves the answer complete on screen.

**Rule 6 is a benefit, not a defect.** An earlier reading of this seam called "no persistence" a problem to solve. It is the opposite. The translation is for the reader and for nobody else. Keeping it out of the transcript keeps it out of the agent's context, out of an export, and out of a resumed session, so a bad translation can never become a fact the agent reasons about. This bounds the blast radius of the whole product to one terminal.

## Consequences

**The reader waits with the last line missing.** The hook blocks the render of the delta it answers. While the two model calls run, the reader sees the answer without its final line. When a message ends on a newline the final delta is empty, and nothing is held back. This is inherent: to add anything, the last delta must wait.

**`verbose` discards the translation, and the sidecar cannot find out.** The measurement confirms it on 2.1.251. The hook fires, builds its output, and the harness throws the work away. There is no acknowledgement channel, so the sidecar pays for a translation that nobody sees. This gap is open and it moves to the prototype ticket.

**A translation costs two model calls per qualifying message, not per text block.** A tool call ends an assistant message, so a message carries one text block. See the `text block` entry in `CONTEXT.md`.

**Mermaid is out of scope.** The terminal is the only surface the translation reaches, and a terminal draws Mermaid as raw syntax. The diagram menu keeps its fenced forms and loses Mermaid for good.

**Exactly one `MessageDisplay` hook may return `displayContent`.** Two hooks that both answer race, and the last result to arrive wins. The sidecar must detect a second hook and say so.

## Measurements

Six probes against CLI 2.1.251 on 2026-08-29 support this decision. See [`docs/research/seam-measurements.md`](../research/seam-measurements.md) and the fixture in [`docs/prototypes/seam-probe/`](../prototypes/seam-probe/).
