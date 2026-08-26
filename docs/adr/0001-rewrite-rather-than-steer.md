# Re-write the output, do not steer the generation

## Status

accepted

## Decision

Say That Again applies a style with a **second model call that re-writes finished assistant text**. It does not apply a style by putting instructions in the agent's system prompt.

## Why

A style instruction in the system prompt competes with the conversation, and it loses. Observed behaviour: the model follows the style about 80 % of the time at the start of a conversation, and close to 0 % by the end. The instruction is one small block at the head of a context window that then fills with code, tool output, and errors. Every token that arrives after it dilutes it.

A re-write call has no such decay. It is short, it is fresh, and it holds one job, so its reliability does not fall as the session grows.

The purpose of this tool is a response that is **always** correctly styled. A mechanism that degrades through the session cannot give that.

## The price, and why we pay it

Steering costs nothing. Re-writing costs one extra model call for every assistant message.

We pay it. An output the reader understands is one of the highest-leverage improvements available to an agent session, and one model call is cheap against that.

## Considered and rejected

**A forcing plugin output style.** It appends style instructions to the system prompt and cannot be switched off by the reader's display settings. Its styled text also becomes the transcript and the model's own context, which a re-write never does. Rejected for one reason: it is a request the model may ignore, and it ignores it more as the conversation grows. Reliability beats reach.

## Consequence

A re-write call is **more reliable, not deterministic**. The re-writer is still a model. It can drop a number, change a file path, or reverse a negation.

The difference is that its failures do not grow with the conversation, and they are cheap to detect, because the original text is available to compare against. That comparison is therefore not optional — it is the mechanism that makes the reliability claim true.
