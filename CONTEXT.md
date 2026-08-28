# Say That Again

A sidecar that translates a coding agent's assistant messages into a style the reader selects, so the reader understands them.

## Language

**Harness**:
The coding agent application that produces the assistant messages. Say That Again attaches to it and does not replace it.
_Avoid_: Host, client, IDE

**Sidecar**:
A process outside the agent's own loop that observes assistant output and produces a styled version of it.
_Avoid_: Plugin, wrapper, filter

**Original**:
The assistant text as the agent produced it, before any style is applied.
_Avoid_: Source text, raw message, input

**Translation**:
The styled version of an original. A model call reads the original and writes it.
_Avoid_: Re-write, transformation, output

**Style**:
The selected way a translation must read. A style includes the language it is written in.
_Avoid_: Voice, tone, persona, format

**Fidelity**:
The property that a translation says what its original said, and no more.
_Avoid_: Accuracy, faithfulness, correctness

**Fidelity check**:
The test that pulls the byte-for-byte items out of an original and tests that the translation holds each one. It makes no model call, and it runs in a test harness, not in front of the reader. See [ADR 0005](docs/adr/0005-the-fidelity-check-is-a-test-instrument.md).
_Avoid_: Validator, guard, verifier, judge

**Label**:
An identifier in an original that the reader uses to point back at it, such as a question number or an option letter.
_Avoid_: Reference, tag, marker

**Ask**:
The request an original ends with: a question to the reader, or a recommended next step.
_Avoid_: Call to action, CTA, prompt

**Diagram**:
A picture of one point in an original, drawn only from what that original states.
_Avoid_: Visual, figure, chart

**Steering**:
The rejected alternative to a translation: placing style instructions in the agent's system prompt so the agent writes in the style itself. See [ADR 0001](docs/adr/0001-rewrite-rather-than-steer.md).
_Avoid_: Prompting, system-prompt styling

**Style decay**:
The fall in how often a model obeys a style instruction as a conversation grows. The reason steering is rejected.
_Avoid_: Drift, instruction fatigue

**Seam**:
The point at which the sidecar attaches to the harness, and by which a translation reaches the reader.
_Avoid_: Hook, integration point, attachment

**Reader**:
The person who reads the translation.
_Avoid_: User, customer, consumer

**Text block**:
One run of assistant prose in a message. A message that holds prose, a tool call, then more prose holds two text blocks. The text block is the unit the sidecar re-writes. See [ADR 0002](docs/adr/0002-re-write-assistant-text-blocks-only.md).
_Avoid_: Chunk, segment, paragraph, flush

**Gate**:
The length test that decides if a text block gets a re-write. A text block longer than 200 characters passes the gate.
_Avoid_: Threshold, filter, minimum length
