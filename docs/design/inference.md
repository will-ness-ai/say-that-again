# Inference

How the sidecar calls a model. The decision is [ADR 0007](../adr/0007-one-model-through-openrouter.md); this is the shape a build follows.

## The request

`POST https://openrouter.ai/api/v1/chat/completions`, with `Authorization: Bearer $OPENROUTER_API_KEY`.

```json
{
  "model": "anthropic/claude-haiku-4.5",
  "stream": false,
  "temperature": 0.2,
  "reasoning": { "enabled": false },
  "messages": [
    { "role": "system", "content": "<role + job + glossary — constant>" },
    { "role": "user",   "content": "<the original text block>" }
  ]
}
```

**`stream: false`.** The sidecar already holds the whole text block before it calls, and it must return one complete string to the seam. A stream buys nothing. See [ADR 0006](../adr/0006-attach-at-messagedisplay-and-append-to-the-final-delta.md).

**Reasoning off.** On a task this mechanical, a hidden reasoning phase spends the latency budget on tokens the reader never sees. Not every model accepts the parameter; send it where `supported_parameters` lists `reasoning`.

**`temperature: 0.2`.** A translation is a faithful restatement, not a creative act.

**No token budgets.** Measure the input in characters, as the gate does. The output stays unbounded, because a truncated translation loses the **ask** at the end and stops being a valid thing to reply to.

## Two calls, one after the other

[ADR 0004](../adr/0004-two-call-translation-pipeline.md) sets the order. Call 1 draws diagrams from the original. Call 2 writes the translation and places them. Call 2 needs the output of call 1, so they cannot run together.

Both calls must finish inside the seam's 120 second `timeout`. When the budget runs out, the sidecar prints nothing and the reader keeps the original.

## Caching

The system message is constant for every call: the style's `role`, its `job`, and the glossary. Only the user message changes. A cached input read costs about a tenth of a fresh one, so the constant half is cached and the variable half is not.

This is the largest cost lever in the pipeline, because the constant half is most of the input.

## Failure classes

Every class ends at **fail-open** — print nothing, exit 0, and the harness draws the original. The sidecar tells them apart so that the prototype can report an honest cost, never so that it can behave differently.

| Class | How it shows | What it means |
|---|---|---|
| No key | The variable and `.env` are both absent | The sidecar is not set up |
| Unreachable | The connection fails | No network, or the service is down |
| Timeout | The call passes the budget | The model is too slow for this input |
| HTTP error | A 4xx or 5xx status | A bad request, a bad key, or a service fault |
| Rate limit | 429 | Too many calls |
| Refusal | 200, and the content is empty | The model returned nothing. This is a legal result, not a fault |
| Call 1 failed, call 2 did not | Call 2 runs with no diagrams | A translation with no picture is still correct |

An empty response is the case that must not be confused with a fault. Most text blocks need no diagram, so an empty call 1 is a correct result. See [`translation-pipeline.md`](translation-pipeline.md).

## What is sent, and what is not

[ADR 0002](../adr/0002-re-write-assistant-text-blocks-only.md) bounds this. The request carries one assistant text block, the style, and the glossary. It carries no file from disk, no tool output, no thinking block, and no conversation history.
