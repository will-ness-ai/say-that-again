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
You translate text into pictures. A software agent wrote the text below.
You find the parts that a picture carries better than prose, and you draw those parts.
You draw only what the text already states.
</role>
```

## `job`

```xml
<job>
Pick the smallest view that makes a point clear.

Draw only what the text states. You cannot read the repository, so each path, name, and step
you draw comes from the text itself.

Show logic or an algorithm as pseudocode.
Show runtime control flow as a call tree.
Show structure as a component tree.
Show file responsibility as a shallow file tree.
Show what changes as a diff, when the text already gives the shape that changes.
Show a whole block when most of it is new.

Fence each diagram. On the line above each fence, write one line that names the point it covers.

Most text blocks need no picture. Return nothing when no view makes the text clearer. That is a
correct answer.
</job>
```

## `instructions` (the user prompt)

```xml
Draw the text in <text-block>.
```

## Why each line is here

| Line | The default it beats |
|---|---|
| the smallest view | The model draws the whole system when one branch was the point. |
| only what the text states | The model invents plausible file paths and function names to fill a tree. |
| You cannot read the repository | The model writes as if it had looked, and states its guesses as facts. |
| the six `Show` lines | The model reaches for one favoured form for every subject. |
| Fence each diagram | Unfenced output is unusable to call 2 and to the renderer. |
| one line that names the point | Call 2 must match each picture to a place in the prose. |
| Most text blocks need no picture | The skill this menu comes from assumes a human asked for a picture. This call fires on every text block. |
| Return nothing … a correct answer | The model treats an empty response as failure and produces a weak diagram instead. |

## What was left out of the menu

- **HTML.** The source skill writes one HTML file and opens it with a shell command. A sidecar has no shell, and a browser window for each text block is wrong.
- **Mermaid.** Mermaid does not render in a terminal. Unrendered, it is a wall of syntax that the reader cannot read, which is worse than the prose it replaced. [Where does the sidecar attach, and where does its output go?](https://github.com/will-ness-ai/say-that-again/issues/7) must say whether any seam can render it. If one can, Mermaid returns to the menu for component interaction and data flow.
