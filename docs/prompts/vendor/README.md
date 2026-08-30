# Vendored skills

Third-party skills that go into a prompt **word for word**. `pipeline.py` reads these files at
run time, so what the model receives is what is in this directory. Do not edit them to fit the
project. To change what a call is told, change the blocks around the skill, not the skill.

Both files carry the MIT licence.

| File | Source | Goes into |
|---|---|---|
| `show-me.SKILL.md` | `humanlayer/skills`, `plugins/show-me/skills/show-me/SKILL.md`, commit `6ab9013`, read 2026-08-27 | the whole `<job>` of [call 1](../diagram.md) |
| `stop-slop.SKILL.md` | `hardikpandya/stop-slop`, `SKILL.md`, read 2026-08-29 | a `<stop-slop>` block beside the `<job>` of [call 2](../translation.md) |

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
- **Mermaid came back.** `show-me` offers it, so call 1 drew a sequence diagram once in 16 runs,
  and call 2 passed it to the reader unchanged. Nothing in either prompt says the output goes to a
  terminal, and a terminal renders Mermaid as a wall of syntax.
- **The French closing ask regressed.** S4 lost it on both passes, against 0 of 8 before.
