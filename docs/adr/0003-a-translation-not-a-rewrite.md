# A translation, not a re-write

## Status

accepted

## Decision

The sidecar produces a **translation**. [`CONTEXT.md`](../../CONTEXT.md) previously listed "translation" under _Avoid_ for the term "re-write". That entry is reversed.

## Why

The word is not a label. It is the mechanism. A translator carries meaning across and adds nothing of their own, and each fidelity rule this project needs follows from that one idea:

- A translator does not augment. The glossary is a dictionary, not new material to insert.
- A translator does not renumber. A question numbered 15 arrives numbered 15.
- A translator keeps the speech act. A question arrives as a question.

"Re-write" carries none of these, because a writer authors.

The word also settles how language is handled. English into plain English, and English into French, are the same operation. A style therefore includes the language it is written in, instead of the pipeline taking language as a second input.

## Consequences

- The role in each prompt is a translator. An earlier draft used "technical writer". A writer authors and a translator carries across, so the two pull in opposite directions on the property that matters most.
- [ADR 0001](0001-rewrite-rather-than-steer.md) keeps its original wording. It records a decision that was made before this one.
