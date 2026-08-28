# Fidelity — what a translation keeps, and how we test it

This document answers [What must a re-write keep unchanged, and how do we detect a bad re-write?](https://github.com/will-ness-ai/say-that-again/issues/6).

A translation is worse than no translation when it is fluent and wrong. The reader gets a clean sentence that dropped a number, changed a file path, or reversed a warning, and nothing tells them to doubt it.

## The keep list

[The pipeline](translation-pipeline.md) already names three things that must survive: facts, labels, and asks. "Keep every fact" is one rule that hides three different demands. This table separates them, because only one of the three can be tested by a machine.

| Item | How exact | A machine can test it |
|---|---|---|
| Fenced code blocks | Byte for byte | Yes, and cheaply |
| Text inside backticks — file paths, commands, names | Byte for byte | Yes, and cheaply |
| Labels — `Q15`, `#109`, `Option A` | Byte for byte | Yes, and cheaply |
| List numbers | Byte for byte | Yes, and cheaply |
| Numbers in prose | Same value | Yes, until a translation writes "three" for "3" |
| The ask | Same request, new words | Weakly. A question mark is findable |
| Direction of a negation | Same meaning, no fixed words | **No** |

The last row is the danger, and it is the failure the ticket names. "You must not delete the branch" becomes "You must delete the branch" when one word goes. No test on the text finds that.

**We do not test negation, and we say so.** [Run 01](../prototypes/run-01/README.md) measured the obvious test — count the negation words in each text and compare. The count rose in every one of six translations, from 10 to 11, from 5 to 6, from 7 to 13, and from 12 to 21. A translation legally turns "no `bun install` is needed" into "you do not need `bun install`". No threshold separates that from a reversed warning. A reversed negation is an accepted, undetected risk. The [translation prompt](../prompts/translation.md) carries the rule; nothing verifies it.

## The check

The **fidelity check** pulls the byte-for-byte items out of the original, then tests that the translation holds each one. It makes no model call and runs in milliseconds. [`check.py`](../prototypes/run-01/check.py) is the working version.

**The check is a test instrument, not a run-time gate.** [ADR 0005](../adr/0005-the-fidelity-check-is-a-test-instrument.md) records that decision and why. In short: run 01 put 117 items through the check across six translations and found zero failures, so the check earns nothing in front of the reader today. It earns a great deal behind the prompt, because it turns "this prompt reads well" into a number.

**A third model call as a judge is rejected.** A judge is the same class of machine as the translator. It fails on the same inputs, so a judge that reads a reversed negation as correct is not a check — it is a second opinion from a correlated source. It also costs one more call on a pipeline that already spends two ([ADR 0004](../adr/0004-two-call-translation-pipeline.md)).

### What a failed check does

The ticket offered three actions: show the translation with a warning, show the original, or show both. [ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md) removes one of them. The original stays on screen and the translation is appended below it, so **both are always shown**. "Show the original" is the standing state, not a remedy.

That leaves two actions, and the decision is:

**In a test run, a failed check fails the run.** It names the missing item and the sample. That is the whole point of the instrument.

**At run time there is no check, so there is no action.** The reader always sees the translation.

If later evidence shows a real rate of failure, the run-time action is a **warning**, never suppression. Suppressing the translation gives the reader strictly less: the reader who needs a translation is the reader who could not read the original, so hiding the translation leaves them with the text they already could not read, and no signal that anything happened.

### Writing a check pattern is harder than it looks

The first label pattern in run 01 required a space in front of the label. It therefore missed `**Q5` and `(#111)` and reported a clean pass on eight items where there were eleven. **A check that misses is worse than no check**, because it manufactures confidence. Every pattern needs its own test.

## Code blocks appear two times, and that is correct

The [translation prompt](../prompts/translation.md) says to leave fenced code blocks exactly as they are. ADR 0002 keeps the original on screen. So a code block prints one time in the original and one time in the translation.

We accept that. ADR 0002 states the rule that decides it: **a reader must not have to look up at the original to recover a fact.** A translation with a hole where a code block belongs is not a document the reader can read from top to bottom. Diagrams arrive as fenced blocks too, so one rule covers code and pictures.

## What this does not settle

| Question | Owner |
|---|---|
| A translation runs 8 % to 87 % longer than its original, and the original is still on screen | [A translation is longer than its original, and the reader gets both](https://github.com/will-ness-ai/say-that-again/issues/15) |
| Call 1 draws in the words of the original, and call 2 places the drawing without translating it | [The diagram arrives untranslated — who translates it?](https://github.com/will-ness-ai/say-that-again/issues/16) |
| How much delay the calls add, and what the reader sees while they run | [What is the latency budget, and does the re-write stream?](https://github.com/will-ness-ai/say-that-again/issues/8) |
| Whether the fidelity rules may live in a style at all | [Where do the fidelity rules live — in the style, or in machinery?](https://github.com/will-ness-ai/say-that-again/issues/13) |
