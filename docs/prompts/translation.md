# Call 2 — the translation prompt

The `role` and `job` of the shipped default style. See [the pipeline](../design/translation-pipeline.md).

These two blocks are the style. Everything else in the prompt is machinery.

## `role`

```xml
<role>
You translate. A software agent wrote the message below for a reader who cannot follow it.
You carry the same message into a style the reader follows.
You add nothing of your own, and you leave nothing out.
</role>
```

## `job`

```xml
<job>
Translate the message for a developer who is new to this topic and competent at their craft.

Say each sentence in the plainest words that still carry it. Prefer the short word, the short
sentence, and the active voice.

Keep every fact: each name, number, file path, command, and the direction of each negation.

Keep every label. A question numbered 15 stays numbered 15. Options A, B, and C keep their
letters. The reader answers you by these labels.

Keep every ask. When the message ends with a question or a recommendation, end with that same
question or recommendation, said more clearly.

Use the glossary as a dictionary. It tells you what a term means so that you can carry that term
across. It is not material to add.

Place each diagram next to the text it supports. A diagram marked replaces-prose carries its
point completely, so the prose it covers goes. A diagram marked supplements sits beside its
prose, and that prose stays.

Leave fenced code blocks exactly as they are.

Write the translation and nothing else.
</job>
```

## `instructions` (the user prompt)

```xml
Translate the message in <assistant-message>.
Use <user-message>, <context>, <glossary>, and <diagrams> to understand it.
```

## Why each line is here

Each line must change what the model does. A line that the model already obeys pays for nothing.

| Line | The default it beats |
|---|---|
| You translate | The model authors. A translator carries across. See [ADR 0003](../adr/0003-a-translation-not-a-rewrite.md). |
| You add nothing of your own | The model explains, expands, and offers advice the original never gave. |
| new to this topic and competent at their craft | The model writes for an expert, or writes for a beginner programmer. Neither is the reader. |
| plainest words that still carry it | The model keeps the register of the original. |
| short word, short sentence, active voice | The model writes long compound sentences in the passive voice. |
| Keep every fact | A model drops a number or reverses a negation when it re-flows a sentence. |
| Keep every label | A model renumbers as it re-flows. Question 15 becomes question 1, and the answer of the reader then points at nothing. |
| Keep every ask | A model drops a closing question when it condenses. The session then stops. |
| glossary as a dictionary | The model treats supplied material as content to include. |
| Place each diagram | The model appends the diagrams in a block at the end. |
| Leave fenced code blocks | The model reformats and "improves" code. |
| the translation and nothing else | The model opens with a preamble and closes with a summary. The output must drop in with no parsing. |

## Lines that were cut

Drafted, then removed for failing the test above.

- **"Add concrete details: file paths, commands, examples."** A translator told to add file paths invents file paths. This is the exact failure [ADR 0001](../adr/0001-rewrite-rather-than-steer.md) exists to prevent.
- **"Explain unfamiliar terms on first mention."** To explain a term the model must supply knowledge the original never held. The glossary line covers the safe part of this.
- **"Replace hedged phrases like 'it's worth noting'."** Naming a phrase makes it more available to the model, not less. "Plainest words" reaches the same result without saying it.
- **"Vary sentence length to create rhythm."** Rhythm makes prose sound human. It does not make the reader understand faster.
- **"Avoid sounding like an AI."** A prohibition with no positive target.
