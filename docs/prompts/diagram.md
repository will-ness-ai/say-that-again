# Call 1 — the diagram prompt

The `role` and `job` of the diagram call. See [the pipeline](../design/translation-pipeline.md).

This call is machinery, not style. A style switches it on or off; a style does not change its text.

Whatever this call returns goes to call 2 whole. Nothing reads or filters it in between — call 2
holds both the original and this answer, so it decides which parts are pictures and which are
worth placing. See [the translation prompt](translation.md).

The form menu is taken from the `show-me` skill. See [the digest](../research/show-me-digest.md) for the source and for what was left out.

The unit is one **text block** that passed the gate, not a whole message. See [ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md).

## `role`

```xml
<role>
You are a technical writer. A software agent has answered a developer, and the
answer is hard to follow. You help that developer understand it, by drawing the parts of the
answer that a picture carries better than prose.

You draw only what the answer already states. You cannot read the repository, so each path,
name, and step you draw comes from the text itself.
</role>
```

## `job`

The form menu at [`parts/show-me.md`](parts/show-me.md), sent as written. It is not restated
here — that file is the single source of truth, and `pipeline.py` reads it at run time. It began
as the `show-me` skill and was then edited; see [where it came from and what
changed](parts/README.md).

## `output-format`

`show-me` has no output contract, because it assumes the agent that draws is the agent that
writes. Call 1 hands its pictures to call 2, so this block is ours:

```xml
<output-format>
Write nothing but diagrams. Give each one a fenced block, and one line
directly above the fence that names its point and how it lands:

  replaces: <the point it covers>    the diagram carries that point completely, and holds every
                                     fact of the prose it covers, so that prose can go.

  supplements: <the point it covers> the diagram illustrates a point that the prose must still
                                     make in words.

Draw each part of the answer that has a shape. A sequence, a tree, a set of options, a
comparison, a flow, a set of conditions, and a change all have a shape. Words are what is left
for the parts that have none, so draw first and leave the words little to carry.

The closing question or recommendation of an answer stays in words. Draw what leads up to it.
</output-format>
```

## `instructions` (the user prompt)

```xml
Draw the answer in <text-block>.
Use <context> to understand it.
```

`<context>` holds the last five exchanges: what the person said, what the agent replied, and
every tool it ran in between with what came back. It is the only thing that tells call 1 what the
conversation was about, and the tool results are often the only place a name in the answer was
ever defined.

## Why each line is here

| Line | The default it beats |
|---|---|
| You are a technical writer … help that developer understand it | Without a stated goal the model optimises for a handsome diagram rather than for a reader who is stuck. |
| You draw only what the answer already states | The model invents plausible file paths and function names to fill a tree. |
| You cannot read the repository | The model writes as if it had looked, and states its guesses as facts. |
| the `show-me` skill | The model reaches for one favoured form for every subject. |
| the menu without Mermaid and HTML | Offered them, the model draws what the reader cannot read. Deleting the bullet beats forbidding the form. |
| `replaces:` / `supplements:` | The mark is a claim about fidelity, not a preference. Without it call 2 cannot tell a picture that carries a point from one that only illustrates it. An explicit `<output-format>` block earns a mark on every diagram; the same rule written into prose earned one on 9 of 12. |
| Draw each part of the answer that has a shape | The model draws one picture and writes the rest of the answer off as prose. Naming the shapes gives it a test to apply to each part. |
| Words are what is left for the parts that have none | This line replaced *"Most answers need no picture. Return nothing when no view makes the answer clearer."* — a standing licence to draw nothing, in the last position call 1 read. The model needs no permission to write prose; it needs a reason to draw. |
| The closing question … stays in words | Call 1 drew a card that summarised the whole answer, the ask included. Call 2 then had one picture that covered everything, placed it last, and the reader never reached the question. |

## What was edited out of the skill

`parts/show-me.md` is a fork, not a copy. Three things were deleted from it, and
[its README](parts/README.md) records them. Two are forms the sidecar cannot deliver:

- **Mermaid.** It does not render in a terminal. Unrendered, it is a wall of syntax that is worse
  than the prose it replaced.
- **One focused HTML file**, which the bullet opens with `Bash(open …)`. A sidecar has no shell.

Cutting the bullet is the whole fix. A model does not reach for a form the menu never showed it,
and a line saying *no Mermaid* would put Mermaid in the context window on every call. Measured:
Mermaid appeared in 1 of 16 diagram answers while the bullet was there, and 0 of 16 after.

If a seam is ever found that renders Mermaid, the bullet comes back from
[the digest](../research/show-me-digest.md), which holds the source as it stood. See
[Where does the sidecar attach, and where does its output go?](https://github.com/will-ness-ai/say-that-again/issues/7).

The third is the closing line of `### guidance`:

> You may use one of these, you may use several, it is unlikely you will use all of them. Use your
> judgement and don't overwhelm the user.

That line was written for an agent that draws one picture beside prose it writes itself. This
sidecar wants the pictures to carry the answer, so the paragraph is gone. The paragraph above it —
*keep only the calls, files, props, states, and boundaries needed* — bounds what goes **inside** a
picture, which is still what we want, so it stays.
