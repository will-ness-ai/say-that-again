# The pipeline runs two model calls, in sequence

## Status

accepted

## Decision

Say That Again produces a translation with two model calls. The first call draws diagrams from the original. The second call writes the translation and receives those diagrams. The second call needs the output of the first, so the two run one after the other.

## Why

Prose is not always the clearest form. A call tree, a file tree, or a diff often carries a point that a paragraph carries badly.

One call cannot hold both jobs well. Drawing needs its own menu of forms and its own judgement about what is worth drawing. Translating needs full attention on fidelity. A single prompt that holds both gives each one less.

## The price

[ADR 0001](0001-rewrite-rather-than-steer.md) accepted one extra model call for each assistant message. This design costs two, and the two cannot run together. The delay before the reader sees anything approximately doubles.

We accept the second call. We do not accept the latency without measurement: [What is the latency budget, and does the re-write stream?](https://github.com/will-ness-ai/say-that-again/issues/8) owns that budget, and this decision is what makes it urgent.

## Consequences

- Zero diagrams is a normal result of the first call, not a failure. Most assistant messages need no picture.
- A style carries a switch that turns the first call off. A style that does not want diagrams does not pay for the call.
- The first call cannot read the repository. It draws only what the original states.
