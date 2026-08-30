# Call 2 — the translation prompt

The `role` and `job` of the shipped default style. See [the pipeline](../design/translation-pipeline.md).

These two blocks are the style. Everything else in the prompt is machinery.

The unit is one **text block** that passed the gate, not a whole message. See [ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md).

Call 2 holds the original, the pictures, and the pen. Every judgement about the output is made
here, in one model call. Nothing between the two calls reads or edits what call 1 returned.

## `role`

```xml
<role>
You are a technical writer. A software agent has answered a developer, and the answer is hard to
follow. You help that developer understand it exactly, by carrying the whole answer into a style
they read.

You translate. The meaning you carry out is the meaning that came in.
</role>
```

## `job`

```xml
<job>
Translate the text for a developer who is new to this topic and competent at their craft.

Say each sentence in the plainest words that still carry it. Prefer the short word, the short
sentence, and the active voice.

Keep every fact, label, and ask. Each name, number, file path, command, and the direction of
each negation survives. A question numbered 15 stays numbered 15 and options A, B, and C keep
their letters, because the reader answers you by them. When the text ends with a question or a
recommendation, close on that same question or recommendation, said more clearly.

<diagrams> holds pictures of this same text. Use the ones that earn their place: put each beside
the point it makes, translate the words inside it, and redraw its borders and columns so they
line up around the new words. Drop a picture that only repeats the sentence next to it, and drop
anything in <diagrams> that is not a picture. A fact inside a picture follows the same rule as a
fact outside one.

The closing question or recommendation is the last line of your answer. Prose and pictures alike
come above it.

Leave a fenced code block in <text-block> exactly as it is.

Write the translation and nothing else.
</job>
```

## `stop-slop`

The [`stop-slop` skill](vendor/stop-slop.SKILL.md), word for word, in its own block beside the
`job`. It rides with every style, so a style does not have to restate it.

Two of its rules argue with the `job` above it, and the `job` wins:

- It asks for **varied rhythm**. This project measured that as a no-op — see *Lines that were
  cut* below.
- It asks the writer to **name the specific thing**. A translator may not invent a fact that the
  original never held. See [ADR 0003](../adr/0003-a-translation-not-a-rewrite.md).

Its reference links (`references/phrases.md` and two others) resolve to nothing inside a prompt.
They are left in, because the file is vendored word for word.

## `instructions` (the user prompt)

```xml
Translate the answer in <text-block>.
Use <context> and <diagrams> to understand it.
```

`<context>` holds the last five user and assistant exchanges, each cut to 600 characters. Both
calls receive the same block.

## Why each line is here

Each line must change what the model does. A line that the model already obeys pays for nothing.

| Line | The default it beats |
|---|---|
| You are a technical writer … understand it exactly | Without a stated goal the model optimises for prose that reads well rather than for a reader who is stuck. "Exactly" is what separates this goal from call 1's. |
| You translate | The model authors. A translator carries across. See [ADR 0003](../adr/0003-a-translation-not-a-rewrite.md). |
| new to this topic and competent at their craft | The model writes for an expert, or writes for a beginner programmer. Neither is the reader. |
| plainest words that still carry it | The model keeps the register of the original. |
| short word, short sentence, active voice | The model writes long compound sentences in the passive voice. |
| Keep every fact | A model drops a number or reverses a negation when it re-flows a sentence. |
| Keep every label … the reader answers you by them | A model renumbers as it re-flows. Question 15 becomes question 1, and the answer of the reader then points at nothing. |
| Keep every ask | A model drops a closing question when it condenses. The session then stops. |
| Use the ones that earn their place | The model places every picture it is given, including the ones that carry nothing. |
| put each beside the point it makes | The model appends the pictures in a block at the end. |
| translate the words inside it | Call 1 draws in the words of the original. Left alone, the reader gets translated prose around an untranslated picture, and a French style writes French around English. |
| redraw its borders and columns | A translated word is a different width. Without this line the model keeps the old borders and the box breaks. |
| drop anything in `<diagrams>` that is not a picture | Call 1 sometimes answers with prose that explains why it will not draw. That prose is not a picture, and this is the line that stops it reaching the reader. |
| A fact inside a picture follows the same rule | A model told to translate a picture treats the picture as art, and it translates `git merge <branch-name>` into words. The keep list does not stop at a fence. |
| The closing question … is the last line | A picture that summarises the whole answer has no single point to sit beside, so the model puts it after the ask. The ask survives and the reader never reaches it. |
| Leave a fenced code block in `<text-block>` | The model reformats and "improves" code. Naming the source separates a code block from a picture, because both are fenced. |
| the translation and nothing else | The model opens with a preamble and closes with a summary. The output must drop in with no parsing. |

## Lines that were cut

Drafted, then removed for failing the test above.

- **"You add nothing of your own, and you leave nothing out."** A prohibition. It names the two
  behaviours it bans and so makes both more available. "You translate" and the keep list reach
  the same result without saying them.
- **"Add concrete details: file paths, commands, examples."** A translator told to add file paths
  invents file paths. This is the exact failure [ADR 0001](../adr/0001-rewrite-rather-than-steer.md) exists to prevent.
- **"Explain unfamiliar terms on first mention."** To explain a term the model must supply
  knowledge the original never held.
- **"Use the glossary as a dictionary."** No `<glossary>` is sent, so the line pointed at nothing. `<context>` is sent, and it is named in the instructions instead.
- **"Replace hedged phrases like 'it's worth noting'."** Naming a phrase makes it more available
  to the model, not less. "Plainest words" reaches the same result without saying it.
- **"A diagram marked replaces-prose carries its point completely … a diagram marked supplements sits beside its prose."** Cut from *this* prompt, and it stays cut: call 2 holds the original and the picture, so it judges coverage itself through "use the ones that earn their place". The mark itself came back on the call 1 side as an explicit [`<output-format>`](diagram.md) block, where it now lands on every diagram rather than 9 of 12. Call 2 is not told to read it.
- **"The ask is the last thing you write. No diagram comes after it."** The right rule in the
  wrong place. Written as a late line in a job that had already told the model to put each picture
  beside its point, it lost to that instruction. The same rule, stated once after the picture
  paragraph, took the French arm from 130/134 to 134/134. See [run 02](../prototypes/run-02/README.md).
- **"Vary sentence length to create rhythm."** Rhythm makes prose sound human. It does not make
  the reader understand faster. `stop-slop` asks for it anyway, in its own words; where the two
  disagree the `job` wins.
- **"Avoid sounding like an AI."** A prohibition with no positive target.
