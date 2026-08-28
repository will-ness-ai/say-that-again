# The `show-me` skill — digest

The source of the form menu that [call 1](../prompts/diagram.md) uses. Read on 2026-08-27.

## Source

- Repository: `humanlayer/skills`, MIT licence.
- Path: `plugins/show-me/skills/show-me/SKILL.md`.
- [Permalink](https://github.com/humanlayer/skills/blob/6ab9013a10c28f5046f7f999549cd5328a0b30d7/plugins/show-me/skills/show-me/SKILL.md), commit `6ab9013`, 2026-08-13.
- One file, 3.3 KB. It points at no other file.

## What it is

A menu of forms, not a procedure. Its frontmatter description: *"Help the user understand the current topic visually with concise diagrams, code-shape sketches, and focused HTML artifacts."*

One governing rule sits at the top: *"Pick the smallest view that makes the key point clear."*

| Form | Fence | Bound to |
|---|---|---|
| Pseudocode | `text` | logic, an algorithm |
| Call tree | `text` | runtime control flow |
| Component tree | `tsx` | UI structure, with source paths |
| Shallow file tree | `text` | file responsibility, a broad refactor |
| Mermaid | `mermaid` | component interaction, control flow, data flow |
| Diff | `diff` | what changes, when the shape already exists |
| Whole block | `ts` | when most of it is new |
| One HTML file | — | too dense for Mermaid, or a real visual UI |

Diff is a modifier, not a peer. The skill shows the same diff mechanism applied to a component tree, a file tree, a call tree, and pseudocode.

Six of eight items open with the same construction: **"Show X as Y"**. Every rule is paired with a worked example in the same breath.

Its closing guidance, in full: *"Place each visual next to the short text it supports. Keep only the calls, files, props, states, and boundaries needed to answer the user's current question or the options to resolve the current discussion point."* and *"You may use one of these, you may use several, it is unlikely you will use all of them. Use your judgement and don't overwhelm the user."*

## Three findings that shaped our design

**It has no gate.** Nothing in the skill decides whether a diagram is worth making. It assumes a human invoked it. Its judgement rules govern which form and how much, never whether. Our call 1 fires on every assistant message, so our prompt adds the gate the source has no need for.

**It assumes the agent holds the codebase.** Its strongest forms need real repository facts: file trees with real paths, component trees annotated with source files, and HTML that *"match[es] the product's colors, type, spacing, and components"*. Our call 1 sees only the original. This is why our prompt states that the model cannot read the repository.

**Its output contract is the opposite of ours.** It says *"Place each visual next to the short text it supports"*, because the same agent draws and writes. It has no marker syntax, no figure numbers, and no way to point at prose. The `replaces-prose` and `supplements` marks are ours, not its.

## What we took, and what we left

Taken: pseudocode, call tree, component tree, shallow file tree, diff, whole block. Also the governing rule about the smallest view, and the placement rule, which we give to call 2 because call 2 holds the pen.

Left out:

- **HTML**, because the skill opens the file with `Bash(open …)`. A sidecar has no shell.
- **Mermaid**, because it does not render in a terminal. See [Where does the sidecar attach, and where does its output go?](https://github.com/will-ness-ai/say-that-again/issues/7).

## Also in that repository

`humanlayer/skills` publishes five plugins: `improve-claude-md`, `narrow-react-prop-types`, `build-iterated-agentic-loop`, `design-control-loop`, and `show-me`.
