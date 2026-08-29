# One model, through OpenRouter

## Status

accepted

## Decision

Say That Again calls **one hosted model through OpenRouter**. Both calls of the pipeline use the same model.

| Item | Value |
|---|---|
| Service | `POST https://openrouter.ai/api/v1/chat/completions` |
| Model | One setting, `model`, used by call 1 and call 2 |
| Default model | `anthropic/claude-haiku-4.5` |
| Key | `OPENROUTER_API_KEY` from the environment |
| Streaming | Off |
| Reasoning | Off, where the model accepts the parameter |
| Sampling | `temperature: 0.2` |

The sidecar reads the key from the environment. When the variable is absent, it reads `.env` at the project root. When it finds no key, that is an ordinary error path: print nothing, exit 0, and the harness draws the original. **Fail-open** covers a missing key, an unreachable service, and an error response, with no new branch.

The request shape and the failure classes are in [`docs/design/inference.md`](../design/inference.md).

## Why

**A local model runner was the alternative, and the author chose hosted.** The trade is real and it is not technical. A local runner keeps every assistant message on the machine and costs no money. A hosted service is faster and better, and it sends the reader's conversation to a third party — for a tool whose whole input is agent transcripts. The prior design chose local. This one chooses hosted, and accepts that cost.

**OpenRouter makes the model a setting rather than a decision.** It is a router, so one API reaches many models. The sidecar speaks one protocol, and the reader changes model without a code change. This matters now, because three open questions — latency, cost, and fidelity — are all properties of the model, and the prototype must be able to try candidates cheaply.

**The default is `anthropic/claude-haiku-4.5` because it protects the fidelity evidence.** [ADR 0005](0005-the-fidelity-check-is-a-test-instrument.md) rests on run 01 passing 117 of 117 items, and run 01 used frontier Claude agents. A cheap relative of that family gives the best chance that the result transfers. It is a starting point, not a finding: the prototype measures cheaper models against the same corpus.

**One model for both calls, not two.** Call 1 draws diagrams and call 2 writes prose, so a cheaper model for call 1 is tempting. It is premature. Two models double the settings, double the failure classes, and split the measurement before there is any measurement to split.

## Consequences

**A qualifying message costs money.** One message is about 2 700 input tokens and 1 050 output tokens across the two calls.

| Model | $/Mtok in | $/Mtok out | Per message | Per 100 messages |
|---|---|---|---|---|
| `anthropic/claude-haiku-4.5` | 1.00 | 5.00 | $0.008 | $0.80 |
| `google/gemini-3.1-flash-lite` | 0.25 | 1.50 | $0.002 | $0.23 |
| `google/gemini-2.5-flash-lite` | 0.10 | 0.40 | $0.0007 | $0.07 |

Prices read from the OpenRouter model list on 2026-08-29.

**Cache the constant half of the prompt.** A cached input read costs $0.10 per million tokens against $1.00 for a fresh read — ten times less. The style and the glossary do not change between calls, and they are most of the input. The prototype must cache them.

**`verbose` makes the bill worse than it looks.** The sidecar pays for both calls and the reader sees nothing, because the harness discards the result with no signal. See [ADR 0006](0006-attach-at-messagedisplay-and-append-to-the-final-delta.md).

**The fidelity evidence must be measured again.** [`check.py`](../prototypes/run-01/check.py) and the run 01 corpus already exist, so this is a cheap re-run against the chosen model. Until it runs, ADR 0005's claim holds for frontier agents and not for the thing we ship.

**Assistant text leaves the machine.** [ADR 0002](0002-re-write-assistant-text-blocks-only.md) already bounds what is sent: one assistant text block, the style, and the glossary. No files on disk, no tool output, no thinking blocks, and no conversation history. The reader sets the data policy on their own OpenRouter account; this repository holds no key.

**A hosted call fails in shapes a local runner does not.** An HTTP status, a rate limit, and a moderation refusal are all new. They all end at the same place — fail-open — but the prototype must tell them apart to report an honest cost.
