# Prototype run 02 — the sidecar end to end

The first run of the whole sidecar against a running harness. It answers [Prototype: build the sidecar end to end, and see what it costs the reader](https://github.com/will-ness-ai/say-that-again/issues/18).

[Run 01](../run-01/README.md) put four saved messages through the pipeline, one model call for each part, each call in a fresh frontier agent. This run is the real path: the seam of [ADR 0006](../../adr/0006-attach-at-messagedisplay-and-append-to-the-final-delta.md), the gate of [ADR 0002](../../adr/0002-re-write-assistant-text-blocks-only.md), the two calls of [ADR 0004](../../adr/0004-two-call-translation-pipeline.md), and the inference source of [ADR 0007](../../adr/0007-one-model-through-openrouter.md), attached to a live conversation.

| Item | Value |
|---|---|
| CLI version | 2.1.251 |
| Date | 2026-08-29 |
| Model | `anthropic/claude-haiku-4.5`, and `google/gemini-2.5-flash-lite` for one arm |
| Corpus | The four run 01 samples, unchanged |
| Live probes | 5 |
| Model calls | about 85 |
| Money spent | about $0.20 |

## Files

| File | Job |
|---|---|
| `pipeline.py` | The gate, call 1, call 2, and the OpenRouter request. The live path and the corpus path both use it. |
| `sidecar.py` | The hook program. Buffers the deltas of one text block, then answers the final one. |
| `discard.py` | Looks for the modes that throw a translation away, before a call is spent. |
| `hook.sh` | The `MessageDisplay` hook entry. |
| `styles/plain.json` | The shipped style. |
| `styles/bare.json` | The same style with the fidelity rules deleted. The test for verdict 3. |
| `bench.py` | Runs the run 01 corpus through the real pipeline, and scores it with the run 01 check. |
| `settings.sh`, `run-tty.sh` | Write the settings file, and drive a live terminal through `tmux`. |
| `out/` | The translations and the scores of each corpus arm. |

`settings.json`, `state/`, `panes/` and `work/` are generated and are not committed. They hold machine file paths and real conversation.

## Run it again

```sh
python3 docs/prototypes/run-02/bench.py --model anthropic/claude-haiku-4.5 --style plain --repeat 3
STA_TAG=solo docs/prototypes/run-02/run-tty.sh "Explain how git rebase differs from git merge."
```

The live runner needs `tmux` and an `OPENROUTER_API_KEY` in `.env` at the project root.

## What the reader gets

One live probe, unedited. The original is above the rule, and the translation is below it.

```
⏺ Git merge combines two branches by creating a new commit that joins them together. The
  original commits from both branches stay in the history. This creates a branching timeline
  that shows where development happened in parallel.

  ...

  Which approach do you prefer for this repo?

  ───────────── say that again ─────────────

  Git merge joins two branches by making a new commit that ties them together. All the old
  commits from both branches stay in your history. You see a timeline that branches and shows
  work that happened at the same time.

  ...

  MERGE: Creates branching timeline
  ┌─────────────────────────────────────┐
  │  main:    A ─── B ─── C             │
  │  feature: D ─── E ─── M (merge)     │
  │  History preserved, both paths      │
  │  visible, non-linear                │
  └─────────────────────────────────────┘

  ... two more boxes ...

  Which approach do you prefer for this repo?
```

The construction of [ADR 0006](../../adr/0006-attach-at-messagedisplay-and-append-to-the-final-delta.md) works. The original streams untouched, the translation lands below it, and the ask survives at the end.

---

## The seven verdicts

### 1. Latency

The reader waits **at the end of the message, not during it**.

| Measurement | Value |
|---|---|
| Hook cost on a delta that is not final | 46 ms median of 10 runs |
| Deltas in a live 1234-character text block | 7 |
| Added cost across the whole stream | about 0.3 s |
| Hold on the final delta, live | 7.5 s to 8.8 s |
| Hold on the final delta, corpus, Haiku 4.5 | 8.6 s median, 13.4 s worst of 12 |
| Hold on the final delta, corpus, Flash-Lite | 3.9 s median, 5.6 s worst of 8 |

Call 1 takes about 40 % of the wait and call 2 about 60 %.

The message streams at full speed. Then the last line stops. The harness draws no spinner for a hook, so the screen is still for eight seconds, and nothing tells the reader why. The 120 s `timeout` of ADR 0006 is 14 times the median wait, so it is a fail-safe, not a budget.

**The gap the reader sees is the whole problem.** The sidecar cannot fill it, because the seam gives no in-band route: `systemMessage` is discarded on this event.

### 2. Conversation context

**The control arm did not lose meaning, and the gate is the reason.**

A two-turn live probe was built to break it. Turn 1 asked for a bare recommendation. Turn 2 asked "Why not the other one?" — a question whose answer looks meaningless on its own. The answer was not meaningless:

> Rebase breaks worktree workflows. When you rebase a branch in one worktree, other worktrees checking out that branch encounter conflicts and lost history references.

The reply names its own subject in its first four words, so the translation with no context kept every fact.

This is not luck. **A reply that needs its question is short, and a short reply fails the gate.** "Yes, that works", "Done", "Run it again with `--force`" are all under 200 characters, so the sidecar never sees them. A reply long enough to pass the gate is an explanation, and an explanation states what it explains.

Run 01 finding 7 reached the same result from the other side: S1 and S3 ran with and without the preceding user message, and each pair passed the same checks. Two runs, two methods, one result.

**Recommendation: send no conversation context, and send no glossary.** Context is not free — it is the input half of the bill, it is a new way for a fact to enter a translation that the original never held, and it makes the fidelity check untraceable.

### 3. Where the fidelity rules live

**In machinery. A style must not be able to delete them.**

Two arms of the same corpus, same model, same two passes. The only difference is the style: `plain` holds the fidelity rules in its `job`, and `bare` deletes them.

| Style | Checks passed | What was lost |
|---|---|---|
| `plain` | 128/134 | 6 backtick facts, 3 of them a check artifact |
| `bare` | 125/134 | 6 backtick facts, 1 number, **and label `Q3`, in both passes** |

The label loss is the finding. `bare` dropped `Q3` from S4 on both passes, and `plain` never dropped it. The rule "Keep every label" is the only difference between the two prompts, and deleting it produced the exact failure the rule exists to beat: the reader answers "Q3" and points at nothing.

`bare` also ran longer, not shorter — S1 grew 67 % against `plain`'s 54 %. A style with fewer rules does not produce a smaller translation; it produces a less faithful one.

**What is left for a style to control** once the rules move: the reader it writes for, the register, the language, and the diagram switch. Those are the fields that make a French style French. The keep list is not a preference, so it does not belong beside them.

### 4. How much text the reader gets

**Less than run 01 measured, and the diagram is now the whole cost.**

| Arm | Median translation length | Worst |
|---|---|---|
| Run 01, frontier agents | 1.44× the original | 1.87× |
| Run 02, Haiku 4.5, `plain` | **1.01×** | 1.54× |
| Run 02, Flash-Lite, `plain` | 1.29× | 2.40× |

Haiku 4.5 writes a translation the same length as its original. With the original left on screen the reader gets **2.0×** the text, not the 2.9× that run 01 measured.

The prose is no longer the cost. In the live probe call 1 drew **1535 characters** of ASCII boxes and call 2 placed all three of them, so more than half of the 2758-character translation is a picture the original never had. Call 1 also spends 433 completion tokens to make them, which is 60 % of what call 2 spends on the whole translation.

Two more results:

- **The mark is unstable, and `supplements` is common.** Of 12 corpus diagram answers on Haiku 4.5, five are marked `replaces-prose`, four carry one or more `supplements`, and three carry no mark at all. Flash-Lite marked every one `supplements`. So run 01 finding 5 — a `supplements` diagram repeats the prose beside it, and the reader gets that point three times — still stands. Which mark the same input gets is not repeatable between runs.
- **The size is not repeatable either.** The same sample, S1, drew 1122, 2086, and 1711 characters on three passes.
- **The diagram lands at the end, not beside its point.** In every live probe call 2 put the boxes after the prose and before the closing ask. The `job` line "Place each diagram next to the text it supports" is not obeyed by this model. The ask does survive, which is what matters most.

**Recommendation: ship with `diagrams: off`.** It removes more than half the text on screen, 40 % of the wait, 37 % of the bill, and one of the two calls, and the corpus shows no fidelity loss it was protecting.

### 5. The diagram is untranslated

**It still is, and the fix is to stop drawing.**

Call 1 draws in the words of the original, and call 2 places the drawing without changing it. Nothing has changed since run 01 finding 6. In the live probe the boxes say "History preserved, both paths visible, non-linear" while the prose beside them says "You see a timeline that branches and shows work that happened at the same time."

The two candidate fixes both cost more than the problem. Translating the diagram in call 2 asks a model to re-flow ASCII art without breaking its alignment. Giving call 1 the style stops call 1 being machinery, so every style then owns a drawing prompt.

Verdict 4 makes the choice cheap: the diagram is 56 % of the screen cost and 40 % of the wait. **Switch call 1 off by default.** The question of what language a diagram is written in then belongs to a style that switches it back on, and that style pays for the answer.

One new fault appeared, and it is the reason not to leave call 1 on unwatched. On S4 the correct answer was no diagram. Haiku 4.5 did not return nothing. It returned prose that explains why it will not draw:

> I don't see a view that makes this text clearer than prose. The text is a decision rationale with three supporting elements…

That happened in **three of the five S4 runs** — 845, 848, and 681 characters of unfenced prose — and every one of them was sent to call 2 inside `<diagrams>` as if it were a picture. Call 2 ignored it each time. Nothing in the pipeline makes that safe, and nothing detects it: an unfenced answer is not an empty answer. The prompt line "Return nothing … That is a correct answer" does not hold on this model.

### 6. The silent discard

Three parts. All three are measured.

**What the reader experiences.** A live probe ran with `--verbose`. The sidecar spent 8.81 seconds and $0.0056, produced a complete translation, and the separator never reached the screen. The reader saw the original, in full, with no mark of any kind. It reads as **"the sidecar is off"**, not "the sidecar is broken" — which is worse, because there is nothing to report.

**Can the sidecar find out first? Yes.** `discard.py` reads three sources that a hook process can reach:

| Source | What it finds |
|---|---|
| The harness command line, by walking up from `getppid()` | `--verbose` |
| The settings files, including the one named by `--settings` | `verbose`, `disableAllHooks`, `allowManagedHooksOnly` |
| The settings files and the plugin cache together | how many `MessageDisplay` hooks are installed |

Under `--verbose` it returned `{"verdict": "discard", "found": {"verbose": "harness command line"}}` on the live run, before either call was made. With detection switched on, the sidecar stands down and spends nothing.

**What it does about it: stay quiet and burn nothing.** The seam discards `systemMessage` on this event, so there is no in-band route to the reader. A sidecar that cannot speak and cannot be seen must not charge for the attempt.

**Two hooks race, and this machine already had two.** The first live probe of this run produced a complete translation, and a *different* translation reached the screen. A second `MessageDisplay` hook was installed on the machine by an enabled plugin, and it won.

This matters twice. The reader saw output the sidecar did not write. And **the second hook is invisible to a settings file** — it is registered by the plugin, and only the plugin cache holds it. A detector that reads settings alone reports one hook and is wrong. `discard.py` reads the plugin cache too, and on the race probe it reported `{"verdict": "race", "display_hooks": 2}` and stood down for $0.

**Recommendation: the sidecar checks for a discard mode and for a second `MessageDisplay` hook on the final delta, before call 1. If it finds either, it prints nothing and spends nothing.** Standing down is the only honest answer when the seam gives no acknowledgement.

### 7. Does the fidelity result survive the real model?

**Not intact. It survives on Haiku 4.5 with one bad translation in twenty. It does not survive on Flash-Lite.**

Twenty corpus runs on `anthropic/claude-haiku-4.5` with the `plain` style, scored by the unchanged run 01 [`check.py`](../run-01/check.py):

| Model | Checks | Failures | What was lost | Cost per message | Median wait |
|---|---|---|---|---|---|
| `anthropic/claude-haiku-4.5` | 335 | 7 (**4 real**) | 4 commands, in one run of 20 | $0.0062 | 8.6 s |
| `google/gemini-2.5-flash-lite` | 134 | 7 | 4 backtick facts, **and 3 eaten asks** | $0.00058 | 3.9 s |

Three of the seven Haiku failures are one string, `` `cat examples.md \| glow` ``, and they are an artifact of the check, not a defect. The `\|` is a markdown table escape. Run 01 kept it because the frontier agent copied the table through unchanged; run 02 replaced the table with a tree, so the command survives as `cat examples.md | glow` and the check counts a lost backslash as a lost fact. **A check that counts a formatting escape as a fact manufactures failures, exactly as run 01 finding 2 warned it would manufacture confidence.**

The four real failures are one run. On one pass S3 came back 30 % **shorter** than its original, and four commands went with the text that was cut: `` `acme/route-cli` ``, `` `cat .route/config.json` ``, `` `route --help` ``, and `` `route ticket-skill add grill-design --when "` ``. The other nineteen runs lost nothing.

Flash-Lite is the arm that fails. It is **10.7 times cheaper** and **2.2 times faster**, and it **ate the closing question three times in eight runs**. An eaten ask stops the session. That is not a cost saving; it is a different product.

**The default model stays where [ADR 0007](../../adr/0007-one-model-through-openrouter.md) put it.** The 117/117 of run 01 does not transfer, and no reading of that number should have been carried into a build. The honest claim is 331 of 335, one bad translation in twenty, and a warning that the check itself over-counts.

---

## What this run also feeds

### Cost model

**Caching does not work, and it was never the largest lever.**

Every one of the 84 model calls came back with `cached_tokens: 0` and `cache_write_tokens: 0`. The `cache_control` mark is sent and is correct. It does nothing, because the constant half of the prompt is too small to cache: **300 tokens for call 2 and 276 for call 1, against a 4096-token minimum on Claude Haiku 4.5.** The prompt would have to grow fourteen times before a cache entry is written, and the harness reports no error when it is not.

The map calls caching "the largest cost lever … at a tenth the price of a fresh read". That claim does not survive the measurement. Across 12 corpus messages:

| Half of the bill | Share |
|---|---|
| Output tokens | **69 %** |
| Input tokens | 31 % |
| The constant style and glossary, inside that input | 9.3 % |
| What perfect caching could save | **8.4 %** |

**Output length is the lever.** Call 1 spends 433 completion tokens on a diagram the reader did not ask for; switching it off removes about 40 % of the bill and 56 % of the text on screen, which is five times what caching could ever return.

Measured cost, two calls per qualifying message: **$0.0062 on Haiku 4.5**, close to the $0.008 that ADR 0007 estimated, and **$0.00058 on Flash-Lite**. `verbose` makes the reader pay it and see nothing.

### Failure and degradation

Three cases are now closed by measurement, and one is new.

- **A failed call costs the translation and nothing else.** Every error path in `pipeline.py` ends at fail-open, and the live probes confirm the original always renders.
- **Call 1 failed and call 2 did not** is handled: call 2 runs with an empty `<diagrams>`, and the translation is still correct.
- **The `verbose` case has an answer.** The sidecar can see it coming and stand down. See verdict 6.
- **New: call 1 can fail by answering.** A prose refusal is not an empty response, so it passes every check the pipeline makes and is sent to call 2 as if it were a diagram. Any build that keeps call 1 must test that the answer is fenced before it forwards it.

### Test strategy

`bench.py` is the smallest test that runs the pipeline against a fixed input and scores the result. It is the shape a build should keep: the corpus, the unchanged check, one arm per model and per style, and `--repeat` so that a rate is visible instead of a single sample.

Two things it shows about the check itself:

- **Repeats matter more than samples.** Four samples run twenty times found a failure that four samples run once did not. The variation is between runs of the same input, not between inputs.
- **`check.py` needs a fix before it is a gate for a prompt change.** It must strip markdown table escapes before it compares, or it will fail a translation that kept every fact.

## What this run does not show

- **One reader, one machine, five live probes.** The live evidence is a handful of git questions, not a working day.
- **Two models, one style, one corpus.** The corpus is the same four samples run 01 used, and it is still not a corpus.
- **No harness setting was tested except `verbose`.** `disableAllHooks`, `allowManagedHooksOnly`, and an untrusted workspace are read by `discard.py` and were never exercised.
- **The race was found, not designed.** A second `MessageDisplay` hook happened to be installed on this machine. A run on a clean machine would have missed it.
- **The gate never rejected anything.** No live text block came in under 200 characters, so the gate is unexercised in a live session.
