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

<diagrams> holds pictures of this same text. A picture reads faster than a paragraph, so let the
pictures carry as much of the answer as they can, and put each one where its point belongs. Words
are what is left for the points that no picture holds.

A line above each picture names its point. Put the picture in your answer, at the point it names.
Then decide what the words around it do. `supplements:` says the words must still make that
point, so keep both. `replaces:` says the picture holds every fact of that point, so cut the
prose that says the same thing again. When a `replaces:` picture leaves out a name, a number, a
path, or a command, keep the words that hold it.

Translate the words inside each picture, and redraw its borders and columns so they line up
around the new words. Drop anything in <diagrams> that is not a picture. A fact inside a picture
follows the same rule as a fact outside one.

Leave a fenced code block in <text-block> exactly as it is.

Check two things before you finish. Every name, number, label, file path, and command of
<text-block> is in your answer, in a picture or in a sentence. The closing question or
recommendation is the last line, below every picture.

Write the translation and nothing else.
</job>
```

## `stop-slop`

[`parts/stop-slop.md`](parts/stop-slop.md), in its own block beside the `job`. It rides with
every style, so a style does not have to restate it. It began as the `stop-slop` skill; see
[where it came from](parts/README.md).

Two of its rules argue with the `job` above it, and the `job` wins:

- It asks for **varied rhythm**. This project measured that as a no-op — see *Lines that were
  cut* below.
- It asks the writer to **name the specific thing**. A translator may not invent a fact that the
  original never held. See [ADR 0003](../adr/0003-a-translation-not-a-rewrite.md).

Its reference links (`references/phrases.md` and two others) resolve to nothing inside a prompt.
They are left in because nothing has measured whether removing them changes an answer.

## `instructions` (the user prompt)

```xml
Translate the answer in <text-block>.
Use <context> and <diagrams> to understand it.
```

`<context>` holds the last five exchanges: what the person said, what the agent replied, and
every tool it ran in between with what came back. Both calls receive the same block.

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
| let the pictures carry as much of the answer as they can | The model treats a picture as a garnish on prose it has already written in full. Against the same corpus, the English arm put 4% of its lines inside a fenced block; with this paragraph, 41%. |
| put each one where its point belongs | The model appends the pictures in a block at the end. |
| Put the picture in your answer, at the point it names | Placement has to be unconditional. A draft that made it conditional on the `replaces:` claim being true had the model fail its own test and drop the picture altogether — 11 of 32 runs reached the reader with no picture at all. |
| `replaces:` … cut the prose that says the same thing again | This is the line that turns a picture into a saving. Without it the model draws *and* writes, and the answer gets longer rather than clearer. |
| When a `replaces:` picture leaves out a name … keep the words that hold it | `replaces:` is call 1's claim, and nothing verifies it. Obeyed blind, it deletes a fact the picture only appeared to carry. |
| Check two things before you finish | Both rules exist earlier in the `job` and both lose to the paragraphs after them. Stated once at the end, as a check rather than a rule, they hold: the French arm went from 3 eaten asks in 8 runs to 1 in 16. |
| translate the words inside it | Call 1 draws in the words of the original. Left alone, the reader gets translated prose around an untranslated picture, and a French style writes French around English. |
| redraw its borders and columns | A translated word is a different width. Without this line the model keeps the old borders and the box breaks. |
| drop anything in `<diagrams>` that is not a picture | Call 1 sometimes answers with prose that explains why it will not draw. That prose is not a picture, and this is the line that stops it reaching the reader. |
| A fact inside a picture follows the same rule | A model told to translate a picture treats the picture as art, and it translates `git merge <branch-name>` into words. The keep list does not stop at a fence. |
| The closing question … is the last line, below every picture | A picture that summarises the whole answer has no single point to sit beside, so the model puts it after the ask. The ask survives and the reader never reaches it. Call 1 is told the same thing from the other side — [*the closing question stays in words*](diagram.md). |
| Leave a fenced code block in `<text-block>` | The model reformats and "improves" code. Naming the source separates a code block from a picture, because both are fenced. |
| the translation and nothing else | The model opens with a preamble and closes with a summary. The output must drop in with no parsing. |

## The line that came back

**"A diagram marked `replaces:` carries its point completely."** This was cut from call 2 once,
on the reasoning that call 2 holds the original *and* the picture, so it can judge coverage for
itself. The mark stayed on the call 1 side, where an explicit `<output-format>` block earned it on
every diagram — and for four merges nothing read it. Call 1 stated, on every run, which pictures
could stand in for prose, and call 2 was never told to look.

Reading the mark is what makes the answer a picture instead of a paragraph. The version that went
in states the placement **first** and the cut **second**, so a doubtful claim costs a paragraph of
prose rather than the picture itself. See [run 02](../prototypes/run-02/README.md).

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
- **"The ask is the last thing you write. No diagram comes after it."** The right rule in the
  wrong place. Written as a late line in a job that had already told the model to put each picture
  beside its point, it lost to that instruction. The same rule, stated once after the picture
  paragraph, took the French arm from 130/134 to 134/134. It now sits in the closing check, which
  is the last thing the model reads. See [run 02](../prototypes/run-02/README.md).
- **"Vary sentence length to create rhythm."** Rhythm makes prose sound human. It does not make
  the reader understand faster. `stop-slop` asks for it anyway, in its own words; where the two
  disagree the `job` wins.
- **"Avoid sounding like an AI."** A prohibition with no positive target.
