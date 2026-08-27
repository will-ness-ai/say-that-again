# Say That Again

A sidecar that re-writes a coding agent's assistant messages into a style the reader selects, so the reader understands them.

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

**Re-write**:
The styled version of an original, produced by a model call that reads the original.
_Avoid_: Translation, transformation, output

**Style**:
The selected way a re-write must read.
_Avoid_: Voice, tone, persona, format

**Steering**:
The rejected alternative to a re-write: placing style instructions in the agent's system prompt so the agent writes in the style itself. See [ADR 0001](docs/adr/0001-rewrite-rather-than-steer.md).
_Avoid_: Prompting, system-prompt styling

**Style decay**:
The fall in how often a model obeys a style instruction as a conversation grows. The reason steering is rejected.
_Avoid_: Drift, instruction fatigue

**Seam**:
The point at which the sidecar attaches to the harness, and by which a re-write reaches the reader.
_Avoid_: Hook, integration point, attachment

**Reader**:
The person who reads the re-write.
_Avoid_: User, customer, consumer

**Text block**:
One run of assistant prose in a message. A message that holds prose, a tool call, then more prose holds two text blocks. The text block is the unit the sidecar re-writes. See [ADR 0002](docs/adr/0002-re-write-assistant-text-blocks-only.md).
_Avoid_: Chunk, segment, paragraph, flush

**Gate**:
The length test that decides if a text block gets a re-write. A text block longer than 200 characters passes the gate.
_Avoid_: Threshold, filter, minimum length
