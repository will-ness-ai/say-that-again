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
| `styles/french.json` | The same style, written in French. The test for verdict 5 — an English style cannot show a language seam. |
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

## Use it in a real session

Copy `pipeline.py`, `sidecar.py`, `discard.py`, `styles/` and a `hook.sh` that sets the defaults into `~/.claude/say-that-again/`, put the key in a `.env` beside them, then register the hook in `~/.claude/settings.json`:

```json
"MessageDisplay": [
  { "hooks": [{ "type": "command", "command": "<install>/hook.sh", "timeout": 120 }] }
]
```

One setting differs from the measurement runs: `STA_DETECT` is `on`, so the sidecar spends nothing when the harness will discard its answer. `diagrams` stays `on` — the author ruled it, and the picture is the point.

**The prompts changed after the measurement runs.** See [the prompt rewrite](#the-prompt-rewrite) below, so a re-run of `bench.py` will not reproduce the tables above exactly. The scores after the rewrite: **200/201** on the English arm and **134/134** on the French arm, against 198/201 and 130/134 before it.

Installing found two faults that the probes hid, and both are fixed here:

- `harness_argv()` tested for `--settings`, which only a probe passes. A real session has no such flag, so `--verbose` was never found. It now walks to the first ancestor that names `claude` and is not part of the sidecar.
- `load_key()` started its search one directory above itself, so a `.env` beside the sidecar was never read.

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

#### The author overruled this

`<context>` now goes to **both** calls: the last five user and assistant exchanges, each cut to 600 characters. The recommendation above measured only whether context was *needed* to keep the facts. It was not. What it never measured is whether context makes the translation better to read, which is the reason it was asked for.

What the change cost, over two passes on each arm:

| | Without context | With context, and the two vendored skills |
|---|---|---|
| English, `plain` | 200/201 | 133/134 |
| French | 134/134 | 132/134 |
| Prompt tokens per message | ~1,840 | ~4,200 |
| Cost per message | $0.0065 | $0.0084 |

The fidelity risk the recommendation named did not appear: no translation pulled a fact out of `<context>` that the text block did not hold. The bill did move, and the two changes are entangled — `<context>` and the vendored skills landed together — so no part of the 29 % is attributable to one of them alone.

No glossary is sent. That half of the recommendation stands.

The corpus stores no conversation history, so the context used by the bench is **synthetic**: five exchanges written per sample to match its topic, in [`context.json`](context.json). The live sidecar reads the real transcript.

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

**The author ruled `diagrams: on`** — the picture is the point of the sidecar, and a cost verdict does not overrule that. What follows was measured after the ruling.

### 5. The diagram is untranslated

**It still is, and the fix is to stop drawing.**

Call 1 draws in the words of the original, and call 2 places the drawing without changing it. Nothing has changed since run 01 finding 6. In the live probe the boxes say "History preserved, both paths visible, non-linear" while the prose beside them says "You see a timeline that branches and shows work that happened at the same time."

The two candidate fixes both cost more than the problem. Translating the diagram in call 2 asks a model to re-flow ASCII art without breaking its alignment. Giving call 1 the style stops call 1 being machinery, so every style then owns a drawing prompt.

**The author ruled: keep the diagram, and have call 2 translate it.** Three lines were added to the style's `job` — translate the words inside a diagram, keep its shape, keep a name and a path and a command exactly, and treat only what `<diagrams>` holds as a diagram, because a code block is fenced too and the two instructions otherwise contradict each other.

A French style was written to test it, because an English style cannot show a language seam. It works:

```
┌─────────────────────────────────────────────────────────────┐
│ Dialogue de confirmation : Ouvrir (→ public)                │
├─────────────────────────────────────────────────────────────┤
│ Cela rend l'historique complet des messages de #x lisible   │
│ par ~N membres vérifiés. Une fermeture ultérieure ne       │
│ défait pas cela. Continuer ?                               │
│                    [Confirmer]  [Annuler]                   │
└─────────────────────────────────────────────────────────────┘
```

The labels, the prose inside the box, and the buttons are all French. The box is intact, and `#x`, `~N`, `60s`, `public` and `private` survived. Run 01 finding 6 is closed.

Three costs came with it, all measured on the French arm:

- **The alignment broke on any line the model rewrote.** The right border drifted, and this was first read as a limit of the model. It was a missing instruction: the `job` asked the model to keep the shape of the diagram, and never asked it to redraw the borders around the new words. One line — *redraw its borders and columns so they line up around the new words* — fixed it. See [the prompt rewrite](#the-prompt-rewrite).
- **The translation grows.** The French arm ran 1.23× to 2.34× the original, against 1.01× median for the English arm. A style that changes language pays for the diagram twice: once to draw it, once to re-write it.
- **The diagram buries the ask.** This is the one that matters, and it is new.

#### The diagram buries the ask

The French S1 holds its closing question — `Êtes-vous d'accord ?` — and then two diagram blocks after it. The reader scrolls to the end and finds a box, not a question. The ask is kept and lost at the same time, and [`check.py`](../run-01/check.py) catches it because it tests the last character.

A prompt line was written for it: *"The ask is the last thing you write. No diagram comes after it."* It did not work, and this was recorded as **"the fix is machinery, not a prompt"** — the sidecar would move trailing fences above the closing paragraph after call 2 returned.

**That conclusion was wrong.** The line was added last, to a `job` that had already told the model to *place each diagram next to the text it supports*. The later instruction won. Stated once, after the picture paragraph instead of before it — *The closing question or recommendation is the last line of your answer. Prose and pictures alike come above it.* — the same rule took the French arm from 130/134 to **134/134**, with the ask last in all eight runs. No machinery is needed. See [the prompt rewrite](#the-prompt-rewrite).

#### The refusal that is not empty

One new fault appeared, and it is the reason not to leave call 1 on unwatched. On S4 the correct answer was no diagram. Haiku 4.5 did not return nothing. It returned prose that explains why it will not draw:

> I don't see a view that makes this text clearer than prose. The text is a decision rationale with three supporting elements…

That happened in **three of the five S4 runs** — 845, 848, and 681 characters of unfenced prose — and every one of them was sent to call 2 inside `<diagrams>` as if it were a picture. Call 2 ignored it each time. The prompt line "Return nothing … That is a correct answer" does not hold on this model.

Three things drive it. A chat model cannot really return nothing, so told to produce an absence it produces the most chat-like thing available: an explanation of the absence. The instruction has no positive form to obey, unlike "Keep every label". And at `temperature` 0.2 it is not repeatable — S4 refused on two passes and drew a `supplements` diagram on the third, from the same input.

This was first fixed in `pipeline.py`, by dropping any call 1 answer that held no fence. **That fix was removed.** It is parsing between two model calls, it is lossy — a real picture that arrives with a prose preamble is thrown away whole — and call 2 already holds both the original and the answer. One line in the `job` does the same job and discards nothing: *drop anything in `<diagrams>` that is not a picture*. Across the 20 runs since, no refusal has reached the reader. See [the prompt rewrite](#the-prompt-rewrite).

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

#### Re-measured after the prompt rewrite

The eaten ask was the whole case against Flash-Lite, and [the prompt rewrite](#the-prompt-rewrite)
was aimed at exactly that defect. Both arms were run again against the rewritten prompts:

| Model | Runs | Checks | Failures | What was lost | Cost per message |
|---|---|---|---|---|---|
| `anthropic/claude-haiku-4.5` | 12 | 200/201 | 1 | 1 buried ask | $0.0065 |
| `google/gemini-2.5-flash-lite` | 16 | 263/268 | 5 | 5 backtick facts, **0 eaten asks** | $0.00093 |

**Flash-Lite ate no ask in sixteen runs.** The loss was a fault of the prompt, not of the model,
and the sentence "that is not a cost saving; it is a different product" does not survive the
re-measurement. What remains against Flash-Lite is quieter and smaller: it drops a literal string
about once every three runs — `--watch`, `demo-repo/.route/config.json` — where Haiku dropped
none in twelve.

**The default still stays where ADR 0007 put it**, on the higher score. But the gap is now one
fidelity class rather than a broken product, and Flash-Lite is **7 times cheaper** on the same
corpus. Whether that trade is worth taking is a live question again, and it is the author's to
answer, not this run's.

---

## The prompt rewrite

The seven verdicts above were reached against the prompts as they stood. Reading those prompts
afterwards found three faults, and fixing them changed the numbers.

**The prompts named tags that are never sent.** Both `job` blocks documented
`Use <user-message>, <context>, and <glossary> to understand it`, and the `job` of call 2 spent a
paragraph on how to use the glossary. Verdict 2 ruled that no context and no glossary is sent.
The paragraph pointed at nothing and was paid for on every text block.

**The two calls carried a protocol that neither needs.** Call 1 marked each picture
`replaces-prose` or `supplements`, and call 2 held a paragraph that read the mark. Call 2 already
holds the original *and* the picture, so it can judge coverage for itself — and call 1 emitted the
mark in only 9 of 12 runs, so a third of the time call 2 read a signal that was not there. Both
sides were cut, and replaced with *use the ones that earn their place*.

**Code was parsing what call 1 returned.** `draw()` dropped any answer that held no fence, to
catch the prose refusal. That is lossy — a real picture that arrives with a prose preamble is
thrown away whole — and it puts a filter between two model calls that only one of them needs.
Cut, and replaced with one line in the `job` of call 2: *drop anything in `<diagrams>` that is not
a picture*.

Removing the filter made the pipeline honest, and it exposed a defect the filter had been hiding:
S4 now got a picture, and the picture landed after the closing question. That is the same buried
ask the French arm had shown, now visible in English, twice in three passes.

### The buried ask was a prompt problem

The rule had been written before and had failed, and the failure was recorded as proof that the
fix must be machinery. The rule was not wrong; its **position** was. It sat before the paragraph
that told the model to place each picture beside its point, and that later paragraph won.

Moved to a single statement after the picture paragraph:

> The closing question or recommendation is the last line of your answer. Prose and pictures alike
> come above it.

| Arm | Before the rewrite | After |
|---|---|---|
| English, 3 passes | 198/201 | **200/201** |
| French, 2 passes | 130/134 | **134/134** |
| Flash-Lite, 4 passes | 3 eaten asks in 8 runs | **0 in 16 runs** |

The `bare` style was rebuilt from the rewritten `plain` with the same fidelity rules removed, and
verdict 3 holds unchanged: it dropped label `Q3` and the fact `read_message_history`, where
`plain` dropped neither. The re-measured Flash-Lite arm is under [verdict 7](#7-does-the-fidelity-result-survive-the-real-model).

The French arm ends every one of its eight runs on the ask. The English arm fails once in three
passes on S4, where call 1 draws a card that summarises the whole answer: it has no single point
to sit beside, so it drifts to the end. That is the last open defect, and it is call 1 drawing the
wrong picture, not call 2 placing it wrongly.

Two other results came from the rewrite. The alignment drift reported under verdict 5 as a limit
of the model was a missing instruction — *redraw its borders and columns so they line up around
the new words* — and the French boxes now close. And the `job` of call 2 fell from 1434 to 1200
characters while scoring higher, so the paragraphs that were cut were not paying for themselves.

### What this changes about the method

A prompt line that fails is not proof that the behaviour needs code. It is one measurement of one
line in one position, inside whatever else the prompt is already saying. The `job` that the failing
line was added to held a dead glossary paragraph, a duplicated fact list, two overlapping rules
about fences, and a protocol for a mark that arrived two-thirds of the time. That is not a fair
test, and the conclusion drawn from it — *build the machinery* — would have shipped code for a
defect that one moved sentence fixes.

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
- **New: call 1 can fail by answering.** A prose refusal is not an empty response, so it passes every check the pipeline makes and is sent to call 2 as if it were a diagram. Any build that keeps call 1 must tell call 2 to use only what is a picture. Do not filter it in code — see [the prompt rewrite](#the-prompt-rewrite).

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
