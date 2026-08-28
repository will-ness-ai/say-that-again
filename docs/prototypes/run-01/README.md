# Prototype run 01 — the pipeline against real assistant messages

The first run of the [translation pipeline](../../design/translation-pipeline.md) on real text. It answers [What must a re-write keep unchanged, and how do we detect a bad re-write?](https://github.com/will-ness-ai/say-that-again/issues/6), and it gives evidence to two other tickets.

Before this run, no message had gone through the pipeline. The prompts were justified by reading. This run replaces that reading with measurement.

## What was run

**Input.** Four assistant text blocks, taken from real coding-agent transcripts on the author's machine. Each block passes the 200-character gate. All four are scrubbed: project names, machine file paths, and session identifiers are replaced with neutral text. The shape and the difficulty of each block are unchanged.

| Sample | Chars | What makes it hard |
|---|---|---|
| [S1](samples/S1.original.md) | 2115 | Labels (`Q5`, `Q2`, `#109`, `#111`), five negations, a closing ask, five backtick facts |
| [S2](samples/S2.original.md) | 848 | A fenced shell block, a copy-and-run command line, twelve backtick facts |
| [S3](samples/S3.original.md) | 1951 | Six tables, 31 backtick facts, a risk warning, a closing ask |
| [S4](samples/S4.original.md) | 1644 | A numbered list, a verdict built on negations, a closing ask |

**Calls.** Ten model calls: four diagram calls, six translation calls. Each call ran in a fresh agent that held only the prompt. The prompts came out of [`docs/prompts/`](../../prompts/) with no change.

**Variants.** S1 and S3 ran the translation call two times: one time with the `<user-message>` tag, one time without it. That pair tests [How much conversation context does the re-writer receive?](https://github.com/will-ness-ai/say-that-again/issues/10).

## The check

[`check.py`](check.py) is the cheap fidelity check, written for this run. It pulls out of the original the items that a translation must keep byte for byte, then tests that the translation holds each one:

- Fenced code blocks
- Text inside backticks — file paths, commands, names
- Labels — `Q5`, `#109`, `Option A`
- List numbers
- Numbers in prose
- The ask — an original that ends with a question needs a translation that ends with a question

It makes no model call. It runs in milliseconds.

```
### S1.paired   11/11 pass   2115 -> 2729 chars (+29%)   negation words 10 -> 11
### S1.bare     11/11 pass   2115 -> 2767 chars (+31%)   negation words 10 -> 11
### S2.paired   12/12 pass    848 ->  915 chars  (+8%)   negation words  5 ->  6
### S3.paired   39/39 pass   1951 -> 3647 chars (+87%)   negation words  7 -> 13
### S3.bare     39/39 pass   1951 -> 3623 chars (+86%)   negation words  7 -> 12
### S4.paired    5/5 pass    1644 -> 2579 chars (+57%)   negation words 12 -> 21

117/117 checks pass. 0 failures.
```

## Findings

**1. The cheap check found no defect.** 117 items, zero failures. Every code block, path, command, label, and number survived. Every ask survived. On this evidence the check earns nothing at run time. It earns its place as a test instrument, which is what [ADR 0005](../../adr/0005-the-fidelity-check-is-a-test-instrument.md) decides.

**2. A first draft of the check under-counted, and said nothing about it.** The first label pattern needed a space in front of the label. It therefore missed `**Q5` and `(#111)`, and reported a clean pass on eight items instead of eleven. A check that misses is worse than no check, because it manufactures confidence. Every pattern needs a test of its own.

**3. The negation count test does not work.** The count of negation words rises in every sample: 10 to 11, 5 to 6, 7 to 13, 12 to 21. A translation legally turns "no `bun install` is needed" into "you do not need `bun install`". No threshold separates that from a reversed warning. This test is rejected, with evidence.

**4. Length is the defect that the check does not measure.** The translations run 8 % to 87 % longer than their originals. [ADR 0002](../../adr/0002-re-write-assistant-text-blocks-only.md) keeps the original on screen, so the reader of S3 gets 5598 characters where the agent wrote 1951. That is 2.9 times the text, to make it easier to read.

**5. A `supplements` diagram repeats the prose beside it.** In [S4](samples/S4.translation.md) call 1 drew the three-part payload as a tree and marked it `supplements`, so the prose stayed. The reader now gets that payload two times inside the translation, and a third time in the original above it.

**6. The diagram never gets translated.** Call 1 draws from the original, and call 2 places the drawing without changing it. In S4 the diagram says "Revisit tripwires", "Explicit non-actions", and "recurring metrics pipeline". None of those phrases is in the translated prose, which says "Triggers to look again", "The non-actions, said out loud", and "repeating metrics pipeline". The diagram is an island of untranslated text inside the translation. A style that writes in French would produce a French translation around an English picture.

**7. The preceding user message changed nothing that matters.** S1 and S3 ran with and without `<user-message>`. Each pair passes exactly the same checks — 11 for S1, 39 for S3. The differences are word choice: "Pre-flight" against "Before you start", "inline" against "straight to the screen". No fact, label, structure, or ask changed.

## What this run does not show

- **Four samples, one model, one style.** The samples are not a corpus. A rate of failure needs many more.
- **No translation failed.** So the run tests the check, and it does not test what the reader sees when a check fails.
- **The model ran as an agent, not as an API call.** A fresh agent holds a system prompt that a bare API call does not hold. The prompt reached it unchanged, but the surrounding conditions are not identical.
- **The user messages were weak.** S1 was answering "agreed", S3 was answering a short instruction list. Neither carried much meaning. Finding 7 does not cover a reply that makes no sense without its question.

## How to run it again

```sh
python3 docs/prototypes/run-01/check.py
```

The check reads [`samples.json`](samples.json) and the files in [`samples/`](samples/). To test a new prompt, put the new translations in `samples/` and run the check again.
