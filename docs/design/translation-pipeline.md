# The translation pipeline

How Say That Again turns an original into a translation. This document answers [Is a style one built-in setting, or an input to a pipeline?](https://github.com/will-ness-ai/say-that-again/issues/5).

## A style is a value the pipeline reads

A style is two pieces of text and one switch:

| Field | Holds |
|---|---|
| `role` | Who the model is. |
| `job` | What the model must do, and what it must keep. |
| `diagrams` | `on` or `off`. |

The pipeline reads these. It does not contain them.

**One style ships.** There is no registry, no editor, and no library of styles. The change against a fixed string in the code is only that the pipeline reads the style from a file. That costs almost nothing today, and it removes the failure the prior design hit: its style lived inside two scripts, so the two copies drifted apart.

**A style includes its language.** A French style is a style whose `job` says to write in French. Language is not a second input. See [ADR 0003](../adr/0003-a-translation-not-a-rewrite.md).

**Everything else is machinery.** The glossary, the context, the user message, the assistant message, and the diagrams are assembled the same way for every style.

### Where a style lives, and how the reader selects one

A style is a file. One file ships as the default. A setting names the file to use. A project setting is stronger than a global setting.

How the reader turns the sidecar off during a session is not decided here. It stays on the map as fog.

## The two calls

Each part of each prompt is wrapped in its own XML tag. [ADR 0004](../adr/0004-two-call-translation-pipeline.md) records why there are two calls.

**The unit is one text block, not one message.** [ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md) set that unit and set the gate: a text block longer than 200 characters passes. The pipeline below runs once for each text block that passes. A message with three qualifying text blocks therefore costs six model calls.

| Prompt part | Call 1 — diagrams | Call 2 — translation |
|---|---|---|
| `role` | translator | translator |
| `job` | draw | translate |
| `glossary` | if present | if present |
| `context` | yes | yes |
| `user-message` | yes | yes |
| `text-block` | yes | yes |
| `diagrams` | — | from call 1 |
| instructions (user prompt) | yes | yes |

The prompt text is in [`docs/prompts/`](../prompts/).

**Call 1 draws only what the original states.** It cannot read the repository. If the original names three files, it can draw those three files. This keeps call 1 to one bounded model call.

**Call 1 may return nothing.** Most text blocks need no picture. Zero diagrams is a correct result.

### The contract between the calls

Call 1 marks each diagram, and names in one line the point that diagram covers:

- `replaces-prose` — the diagram carries that point completely, with every fact of the prose it covers.
- `supplements` — the diagram illustrates a point that the prose must still make.

The mark carries no pointer into the original. Call 2 re-flows the whole text block, so a pointer into the structure of the original points at text that no longer exists. Call 2 holds the original, the diagrams, and the pen, so call 2 decides where each diagram goes.

`replaces-prose` removes prose from the **translation**, never from the screen. [ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md) appends the translation below the original and leaves the original in place, so the reader keeps the prose either way. The fidelity rule still holds: a reader must not have to look up at the original to recover a fact.

### Which forms call 1 may draw

Taken from the `show-me` skill. See [the digest](../research/show-me-digest.md).

| Form | Used for |
|---|---|
| Pseudocode | logic, an algorithm |
| Call tree | runtime control flow |
| Component tree | structure |
| Shallow file tree | file responsibility |
| Diff | what changes, when the original gives the shape that changes |
| Whole block | when most of it is new |

Two forms from `show-me` are excluded:

- **HTML.** The skill opens its HTML file with a shell command. A sidecar has no shell, and a browser window for each assistant message is wrong.
- **Mermaid.** Mermaid does not render in a terminal. It is a wall of syntax that the reader cannot read, which is worse than the prose it replaced. [Where does the sidecar attach, and where does its output go?](https://github.com/will-ness-ai/say-that-again/issues/7) must say whether anything can render it.

## What a translation keeps

A translation says what its original said, and no more. Three things must survive. [`fidelity.md`](fidelity.md) holds the full keep list, what a machine can test, and what it cannot.

**Facts.** Each name, number, file path, command, and the direction of each negation.

**Labels.** A question numbered 15 stays numbered 15. Options A, B, and C keep their letters. The reader answers by these labels, so a changed label makes the answer of the reader point at nothing.

**Asks.** When the original ends with a question or a recommendation, the translation ends with the same question or recommendation, said more clearly. An eaten ask stops the session.

Labels and asks are the same rule: **the translation must still be a valid thing to reply to.** Both are cheap to check. Labels are countable. The last ask is findable.

**The glossary is a dictionary.** It tells the model what a term means, so the model can carry that term across. It is not material to add. This is what keeps the fidelity check possible, because a translation that may explain adds sentences that no check can trace.

## What this does not settle

| Question | Owner |
|---|---|
| How much delay two calls add, and what the reader sees while they run | [What is the latency budget, and does the re-write stream?](https://github.com/will-ness-ai/say-that-again/issues/8) |
| A translation runs 8 % to 87 % longer than its original, and the original stays on screen | [A translation is longer than its original, and the reader gets both](https://github.com/will-ness-ai/say-that-again/issues/15) |
| Call 1 draws in the words of the original, and call 2 places the drawing untranslated | [The diagram arrives untranslated — who translates it?](https://github.com/will-ness-ai/say-that-again/issues/16) |
| Whether the seam can render Mermaid | [Where does the sidecar attach, and where does its output go?](https://github.com/will-ness-ai/say-that-again/issues/7) |
| Whether the fidelity rules may live in a style at all, since a style can delete them | [Where do the fidelity rules live — in the style, or in machinery?](https://github.com/will-ness-ai/say-that-again/issues/13) |
