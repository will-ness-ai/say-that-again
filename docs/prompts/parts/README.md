# Prompt parts

Blocks of prompt text that go into a call as they are written. `pipeline.py` reads these files
at run time and sends what it finds, so **what is in this directory is what the model receives**.

Edit them like any other file in this repository.

| File | Goes into |
|---|---|
| `show-me.md` | the whole `<job>` of [call 1](../diagram.md), 2,286 characters |
| `stop-slop.md` | a `<stop-slop>` block beside the `<job>` of [call 2](../translation.md), 2,337 characters |

## Where they came from

Both started as third-party skills under the MIT licence, and both were forked into this
repository and edited. They are ours now, and they no longer match their source.

| File | Source | Read |
|---|---|---|
| `show-me.md` | `humanlayer/skills`, `plugins/show-me/skills/show-me/SKILL.md`, commit `6ab9013` | 2026-08-27 |
| `stop-slop.md` | `hardikpandya/stop-slop`, `SKILL.md` | 2026-08-29 |

MIT, both. The digest of the first, with the source as it stood, is at
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

## What the calls add around them

Each skill was written for an agent that holds a conversation and a repository, and that both
draws and writes. The sidecar holds neither and splits the two jobs across two calls, so three
gaps are filled by blocks around these files:

- **`show-me.md` has no output contract.** It says *"Place each visual next to the short text it
  supports"*, because the agent that draws is the agent that writes. Call 1 hands its pictures to
  call 2, so `<output-format>` adds the fence rule and the `replaces:` / `supplements:` mark.
- **`show-me.md` assumes a repository.** Its component tree carries real source paths. `<role>`
  states that call 1 cannot read the repository.
- **`stop-slop.md` assumes an author.** It tells the writer to name the specific thing and to cut
  what is not needed. A translation may not add material and may not drop a fact, so `<role>` and
  the style `<job>` bound it. Where the two disagree, the style wins.

Its reference links (`references/phrases.md` and two others) resolve to nothing inside a prompt.
They are left in because nothing has measured whether removing them changes an answer.

## Whether `stop-slop` still earns its place

It is 2,337 characters of prose-quality rules, and the answers it governs are now more than a
third fenced picture. It is paying a full price to police a shrinking share of the output.
Nothing has measured a run without it. That is the next cheap test, and it is one line in
`translate()`.
