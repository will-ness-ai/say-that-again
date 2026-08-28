# Slop patterns — a catalogue

Named patterns of low-quality model prose. Gathered on 2026-08-27 to write the [translation prompt](../prompts/translation.md).

## How to use this

**Do not paste these names into a prompt.** A prohibition makes the banned behaviour more available to the model, not less. The catalogue is here so that a person can judge a translation, and so that a later session can test whether a positive instruction removed a pattern.

The [translation prompt](../prompts/translation.md) reaches these results with positive instructions instead: *"plainest words that still carry it"*, *"short word, short sentence, active voice"*, and *"add nothing of your own"*.

## The patterns

| Pattern | Before | After |
|---|---|---|
| **Hedging** | "It's worth noting that the deployment takes 45 seconds. When it comes to performance…" | "The deployment takes 45 seconds." |
| **Inflated verbs** | "harnesses advanced techniques to facilitate seamless integration" | "uses advanced techniques to integrate smoothly" |
| **False warmth** | "Great question! What a brilliant observation!" | *(cut; answer the question)* |
| **The tricolon** | "Fast. Simple. Effective." | Vary the length. Three parallel clauses is a pattern the model completes, not a rhythm it chose. |
| **Uniform sentence length** | Every sentence 14–22 words. | Length follows the meaning. |
| **The five-paragraph shape** | Introduction, three sections, recap — whatever the content is. | Structure follows the content. |
| **Strategic vagueness** | "many benefits for teams working on complex projects" | "reduces deployment time from 2 hours to 12 minutes" |
| **Corporate adjectives** | "transformative", "cutting-edge", "seamless", "robust" | Name the change instead. |

## What a new reader needs

The **curse of knowledge**: an expert cannot recall not knowing, so they skip steps that feel obvious and are invisible to a newcomer.

Sourced findings, from technical-writing references:

1. Do not assume domain terminology.
2. A named example anchors an abstract point. `npm build` beats "build the project".
3. Give the core idea first, then the detail.
4. Headings and short paragraphs let a newcomer find an answer without reading in order.

**The limit this project puts on that advice.** Points 1 and 2 tell a writer to add material. A translation may not add material. See [ADR 0003](../adr/0003-a-translation-not-a-rewrite.md). The glossary is the one licence to explain a term, and only for a term the glossary already defines.

## Sources, and how far to trust them

The slop patterns rest mostly on one essay, with two secondary references. Treat the list as a working catalogue, not a settled finding.

- [A Field Guide to AI Tells](https://matthewvollmer.substack.com/p/i-asked-the-machine-to-tell-on-itself) — carries most of the patterns above.
- [Common Words and Phrases in AI-Generated Text](https://www.grammarly.com/blog/ai/common-ai-words/) — hedging, inflated verbs.
- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)

Better sourced:

- [Google technical writing: Audience](https://developers.google.com/tech-writing/one/audience)
- [The Curse of Knowledge in Technical Writing](https://earthly.dev/blog/curse-of-knowledge/)
- [Technical Writing Essentials: Communicating with Precision](https://pressbooks.usnh.edu/technicalwriting/chapter/communicatingprecision/)

The prior design asserted the value of a prompt ordering from two runs and then had to withdraw the claim. Do not repeat that here: a claim that one of these instructions improves a translation needs a test, not a reading.
