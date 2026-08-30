# Vendored skills

Third-party skills that go into a prompt **word for word**. `pipeline.py` reads these files at
run time, so what the model receives is what is in this directory. Do not edit them to fit the
project. To change what a call is told, change the blocks around the skill, not the skill.

## What is dropped at read time

The file on disk stays byte for byte what its author published, so it can be diffed against the
source. Every edit happens once, in `vendored()`, and is named here.

**The YAML frontmatter.** It tells a harness *when* to load a skill, and this prompt has already
made that decision. In the context window it is a name, a description and a trigger that describe
work the model is already doing. 451 characters on every call, changing nothing.

**Two forms of `show-me` that this sidecar cannot deliver**, cut as whole bullets with their
worked examples:

| Form | Why it goes |
|---|---|
| Mermaid | It does not render in a terminal. Unrendered it is a wall of syntax, worse than the prose it replaced. |
| One focused HTML file | The bullet ends in `Bash(open …)`. A sidecar has no shell. |

Cutting the bullet is what removes the form. A model does not reach for a form the menu never
showed it, and a line saying *no Mermaid* would put Mermaid in the context window on every call —
see the negation rule in [`writing-for-agents`]. Measured: Mermaid appeared in 1 of 16 diagram
answers while the bullet was there, and in **0 of 16** after it went.

`without_forms()` treats a `- ` line inside a fence as a diff removal, not a bullet, so a form's
worked example travels with it and the `### guidance` section survives.

**The closing line of `show-me`'s `### guidance`**, cut as a whole paragraph:

> You may use one of these, you may use several, it is unlikely you will use all of them. Use your
> judgement and don't overwhelm the user.

It was written for an agent that draws one picture beside prose it writes itself, and it is a
brake on the thing this sidecar wants. The paragraph above it — *keep only the calls, files,
props, states, and boundaries needed* — bounds what goes **inside** a picture, and stays.

`without_paragraphs()` splits on a blank line outside a fence, so a fenced block travels whole.

[`writing-for-agents`]: ../../../CLAUDE.md

Both files carry the MIT licence.

| File | Source | Goes into |
|---|---|---|
| `show-me.SKILL.md` | `humanlayer/skills`, `plugins/show-me/skills/show-me/SKILL.md`, commit `6ab9013`, read 2026-08-27 | the whole `<job>` of [call 1](../diagram.md), 2,286 chars in the prompt |
| `stop-slop.SKILL.md` | `hardikpandya/stop-slop`, `SKILL.md`, read 2026-08-29 | a `<stop-slop>` block beside the `<job>` of [call 2](../translation.md), 2,337 chars in the prompt |

The digest of the first is at [`show-me-digest.md`](../../research/show-me-digest.md).

## What the sidecar has to add around them

Each skill was written for an agent that holds a conversation and a repository, and that both
draws and writes. The sidecar holds neither and splits the two jobs across two calls, so three
gaps are filled by blocks around the skill:

- **`show-me` has no output contract.** It says *"Place each visual next to the short text it
  supports"*, because the agent that draws is the agent that writes. Call 1 has to hand its
  pictures to call 2, so `<output-format>` adds the fence rule and the
  `replaces:` / `supplements:` mark.
- **`show-me` assumes a repository.** Its component tree carries real source paths and its HTML
  form ends in `Bash(open …)`. `<role>` states that call 1 cannot read the repository.
- **`stop-slop` assumes an author.** It tells the writer to name the specific thing and to cut
  what is not needed. A translation may not add material and may not drop a fact, so `<role>`
  and the style `<job>` bound it. Where the two disagree, the style wins.

## Measured costs of vendoring them

Against the run-01 corpus on Haiku 4.5, two passes per arm:

| | Before vendoring | After |
|---|---|---|
| English, `plain` | 200/201 | 133/134 |
| French | 134/134 | 132/134 |
| Constant prompt half | ~300 tokens | ~1,050 tokens |
| Cost per message | $0.0065 | $0.0084 |

Three effects worth naming:

- **The mark is now reliable.** With an explicit `<output-format>` block, all 17 diagrams across
  16 runs carried a mark. The earlier prompt, which asked for the mark inside prose, produced one
  in 9 of 12.
- **Mermaid came back, and then it went.** `show-me` offers it, so call 1 drew a sequence diagram
  once in 16 runs and call 2 passed it to the reader unchanged — nothing in either prompt says the
  output goes to a terminal. Cutting the bullet fixed it: **0 of 16** runs since, and every fence
  in every diagram answer is now `text` or plain.
- **The French closing ask regressed.** S4 lost it on both passes, against 0 of 8 before.

## Whether `stop-slop` still earns its place

`stop-slop` is 2,337 characters of prose-quality rules, and the answers it governs are now more
than a third fenced picture. It is paying a full price to police a shrinking share of the output.
Nothing has measured a run without it. That is the next cheap test, and it is one line in
`translate()`.
