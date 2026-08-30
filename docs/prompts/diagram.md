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

The [`show-me` skill](vendor/show-me.SKILL.md), word for word, frontmatter included. It is not
restated here — the file is the single source of truth, and `pipeline.py` reads it at run time.

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

Most answers need no picture. Return nothing when no view makes the answer clearer. That is a
correct answer.
</output-format>
```

## `instructions` (the user prompt)

```xml
Draw the answer in <text-block>.
Use <context> to understand it.
```

`<context>` holds the last five user and assistant exchanges, each cut to 600 characters. It is
the only thing that tells call 1 what the conversation was about.

## Why each line is here

| Line | The default it beats |
|---|---|
| You are a technical writer … help that developer understand it | Without a stated goal the model optimises for a handsome diagram rather than for a reader who is stuck. |
| You draw only what the answer already states | The model invents plausible file paths and function names to fill a tree. |
| You cannot read the repository | The model writes as if it had looked, and states its guesses as facts. |
| the `show-me` skill | The model reaches for one favoured form for every subject. |
| `replaces:` / `supplements:` | The mark is a claim about fidelity, not a preference. Without it call 2 cannot tell a picture that carries a point from one that only illustrates it. An explicit `<output-format>` block earns a mark on every diagram; the same rule written into prose earned one on 9 of 12. |
| Return nothing … a correct answer | The model treats an empty response as failure and produces a weak diagram instead. |

## What the skill offers that a terminal cannot show

`show-me` is used unedited, so call 1 is offered two forms the sidecar cannot deliver:

- **Mermaid.** It does not render in a terminal. Unrendered, it is a wall of syntax that is worse
  than the prose it replaced. Call 1 drew one in 1 of 16 runs, and call 2 passed it to the reader
  unchanged, because nothing in either prompt says where the output goes.
- **One HTML file**, which the skill opens with `Bash(open …)`. A sidecar has no shell.

Neither is filtered in code. Whether to bound them in the prompt, and whether any seam can render
Mermaid, is open — see [Where does the sidecar attach, and where does its output go?](https://github.com/will-ness-ai/say-that-again/issues/7).
