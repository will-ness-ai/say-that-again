# The fidelity check is a test instrument, not a run-time gate

## Status

accepted

## Decision

The **fidelity check** runs in a test harness, over fixed samples, to measure whether a prompt works. It does not run in front of the reader.

It makes no model call. It pulls the byte-for-byte items out of an original — fenced code blocks, backtick text, labels, list numbers, numbers, and a closing question — and tests that the translation holds each one. See [`docs/design/fidelity.md`](../design/fidelity.md).

A third model call to judge a translation is rejected.

## Why

**The check found nothing on real text.** [Run 01](../prototypes/run-01/README.md) put four real assistant messages through the pipeline and ran six translations through the check. 117 items, zero failures. Every code block, path, command, label, number, and closing question survived. A gate that never fires costs the reader delay and buys nothing.

**A judge is correlated with the translator.** A model asked to grade a translation is the same class of machine that wrote it. It fails on the same inputs. A judge that reads a reversed negation as correct is not a check — it is a second opinion from a source that shares the fault. It also adds a third call to a pipeline that already spends two for each text block ([ADR 0004](0004-two-call-translation-pipeline.md)).

**The prompt needs a number, and nothing else supplies one.** The lines in [`docs/prompts/`](../prompts/) were justified by reading. The prior design asserted a prompt result from two runs and then had to withdraw the claim. A check that runs over fixed samples turns "this reads well" into a count that a later change must beat.

**The reader already has the original.** [ADR 0002](0002-re-write-assistant-text-blocks-only.md) appends the translation below the original and leaves the original on screen. Nothing is hidden from the reader, so a failed check has nothing to reveal that is not already there.

## What this gives up

**A reversed negation reaches the reader.** It is the worst failure this project has, and no cheap test finds it. The [translation prompt](../prompts/translation.md) carries the rule and nothing verifies it. Run 01 measured the obvious test — counting negation words — and the count rose in every one of six translations, so that test is rejected with evidence.

**Four samples are not a corpus.** Zero failures in 117 items is weak evidence for a rate. The decision rests on the cost being wrong, not on the pipeline being proved correct.

## Consequences

- The check is code that ships with the tests, not with the sidecar.
- A change to a prompt must run the check and must not lose an item.
- Each check pattern needs a test of its own. A pattern that silently under-matches reports a clean pass and manufactures confidence. Run 01 hit this: a label pattern missed `**Q5` and `(#111)` and reported eight items where there were eleven.
- If later evidence shows a real rate of failure, the run-time action is a **warning** beside the translation, never suppression. Suppressing gives the reader strictly less than showing them a marked translation.
