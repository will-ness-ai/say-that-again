# Prompt parts

Blocks of prompt text that go into a call as they are written. `pipeline.py` reads these files
at run time and sends what it finds, so **what is in this directory is what the model receives**.

Edit them like any other file in this repository.

| File | Goes into |
|---|---|
| `show-me.md` | the whole `<job>` of [call 1](../diagram.md), 2,286 characters |
| `unslop.md` | a `<unslop>` block **above** the `<job>` of [call 2](../translation.md), 4,813 characters |

## Where they came from

Both started as third-party skills under the MIT licence, and both were forked into this
repository and edited. They are ours now, and they no longer match their source.

| File | Source | Read |
|---|---|---|
| `show-me.md` | `humanlayer/skills`, `plugins/show-me/skills/show-me/SKILL.md`, commit `6ab9013` | 2026-08-27 |
| `unslop.md` | `cursor/plugins`, `pstack/skills/unslop/SKILL.md`, commit `99559f2` | 2026-08-30 |

MIT, both. `cursor/plugins` carries no licence of its own, but the `pstack` plugin inside it
does: MIT, Copyright (c) 2026 Lauren Tan. The same file, byte for byte, is also published at
`roerohan/skills`, `unslop/SKILL.md`.

The digest of `show-me`, with the source as it stood, is at
[`show-me-digest.md`](../../research/show-me-digest.md).

## What was edited out of `show-me`

**The YAML frontmatter.** It tells a harness *when* to load a skill, and this prompt has already
made that decision.

**Two forms this sidecar cannot deliver.**

| Form | Why it went |
|---|---|
| Mermaid | It does not render in a terminal. Unrendered it is a wall of syntax, worse than the prose it replaced. |
| One focused HTML file | The bullet ended in `Bash(open …)`. A sidecar has no shell. |

Deleting a form is what removes it. A model does not reach for a form the menu never showed it,
and a line saying *no Mermaid* would put Mermaid in the context window on every call — see the
negation rule in `writing-for-agents`. Measured: Mermaid appeared in 1 of 16 diagram answers
before the cut, and **0 of 16** after.

**The closing line of `### guidance`** — *"it is unlikely you will use all of them … don't
overwhelm the user"*. It was written for an agent that draws one picture beside prose it writes
itself. This sidecar wants the pictures to carry the answer. The paragraph above it, which bounds
what goes **inside** a picture, stays.

## What was edited out of `unslop`

**The YAML frontmatter**, for the same reason as above.

**The `## Adding soul` section**, and the step in `## Process` that calls it. It asks the writer
to have opinions, to use the first person, and to let some mess in. A translation carries out the
meaning that came in. See [ADR 0003](../../adr/0003-a-translation-not-a-rewrite.md).

**Six rules whose fix is to delete something.** Every remaining rule says *how to say a thing*.
These six said *whether to keep it*, and a translator may not make that call.

| Rule | What it asked | What it did |
|---|---|---|
| 2. Name-dropping | "Pick one, say what was said." | Drops the rest. |
| 3. Superficial -ing phrases | "Delete or expand with real sources." | A translator has no sources. |
| 5. Vague attributions | "Name the source or delete." | Same. |
| 10. Rule of three | "Use the natural number." | Drops list items. |
| 16. Inline-header lists | "Convert those to prose." | Destroys the labels the reader answers by. |
| 21. Cutoff disclaimers | "Find sources or remove." | Drops a hedge the original made. |

Two sentences inside rule 27 went with them, both ending *"Cut it."*

Measured on the English arm, four passes each: the skill as published scored **240/268**, losing
list numbers eight times and labels six times. With these six rules gone, **256 and 262 of 268**
across two runs. The 25 remaining rules are the author's own text, renumbered.

## What the calls add around them

Each skill was written for an agent that holds a conversation and a repository, and that both
draws and writes. The sidecar holds neither and splits the two jobs across two calls, so three
gaps are filled by blocks around these files:

- **`show-me.md` has no output contract.** It says *"Place each visual next to the short text it
  supports"*, because the agent that draws is the agent that writes. Call 1 hands its pictures to
  call 2, so `<output-format>` adds the fence rule and the `replaces:` / `supplements:` mark.
- **`show-me.md` assumes a repository.** Its component tree carries real source paths. `<role>`
  states that call 1 cannot read the repository.
- **`unslop.md` assumes an author.** It tells the writer to name the specific thing. A
  translation may not add material and may not drop a fact, so `<role>` and the style `<job>`
  bound it. Where the two disagree, the style wins — which is why the block sits **above** the
  job rather than below it.

## Whether `unslop` earns its place

It is 4,813 characters of prose-quality rules, and the answers it governs are now more than a
third fenced picture. Against the 2,337-character `stop-slop` it replaced, four passes per arm:

| | `stop-slop` | `unslop` |
|---|---|---|
| English fidelity | 254/268 | 256 and 262 /268 |
| English inside a block | 41 % | 37 % and 36 % |
| French fidelity | 263/268 | 258/268 |
| French inside a block | 43 % | 37 % |
| Call 2 system message | 4,498 chars | 6,968 chars |

Fidelity is a wash — English up about five checks, French down about five. The picture share is
down about five points on both arms, and the prompt is 2.5 KB heavier. Nothing has yet measured
call 2 with **no** editing block at all, which is the test that would say whether either skill
earns its place. That is one line in `translate()`.
