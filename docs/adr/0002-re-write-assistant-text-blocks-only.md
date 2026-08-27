# Re-write assistant text blocks only

## Status

accepted

## Decision

Say That Again re-writes **assistant prose text blocks, on screen, in an interactive terminal**. It changes nothing else.

- The unit is one **text block** — one run of assistant prose in a message. A message that holds prose, a tool call, then more prose holds two text blocks.
- Each text block is tested on its own by the **gate**: a text block longer than 200 characters gets a re-write. A shorter text block does not.
- The sidecar acts on the **completed** text block. The harness sends the block in parts as it streams, so the sidecar collects the parts and waits for the end of the block.
- The re-write is **appended** below the original. The original stays on screen.

These stay untouched:

- Markdown files, and every other file on disk.
- Tool calls, diffs, and command output.
- Thinking blocks.
- Subagent output.
- The agent's plan.
- Print mode, the SDK, the desktop application, and IDE extensions.

## Why

**Files on disk are a second product.** The prior design re-wrote assistant messages *and* the Markdown files the agent wrote. The file half caused most of that system's unsolved problems: it replaced bytes the agent believed it had just written, so the agent's next exact-match edit to that file failed; it blocked the agent loop for up to 180 seconds for each write; and it competed with the screen re-writer for one model runtime, so a file re-write in flight could time out every screen re-write behind it. The one rule that held up across that system's whole history was **display-only**: change rendered text and nothing else. The file hook was the one part that broke it.

**Tool output belongs to the agent, not to the reader.** The only attachment point that can change tool output changes what the **model** reads on its next turn. A styled test log would make the agent reason about text the tool never produced. That is not a display fault. That is a wrong answer.

**Thinking blocks are not addressed to the reader.** Thinking is the model's scratch pad. It is also the largest volume of text in a session, so styling it multiplies the cost for the lowest-value content.

**Subagent output already arrives in scope.** A subagent reports to the main agent, and the main agent writes the summary the reader reads. That summary is an assistant text block. The raw subagent text has no documented route to the screen, so putting it in scope would put an unanswerable question on the route.

**One surface, not five.** The reader reads messages in an interactive terminal. Print-mode output goes to a script. Scoping to the terminal stops later decisions from paying for surfaces that nobody reads.

## The gate, and the evidence against it

The gate is 200 characters, on the whole text block.

The prior system used the same number. Its own critique says the gate *"skips exactly the messages most worth rewriting"*, because short answers are the densest in jargon. That evidence was put to the author, and 200 characters was selected with it in view. The number is a deliberate choice, not an inherited default.

Two smaller faults in the prior gate are not repeated here by construction, because this gate tests the block as it stands: the prior gate stripped fenced code first, and it counted bytes while calling them characters, so it fired early on any text that was not English.

## Consequence

**Append is built out of replace.** The harness offers no append. The hook replaces the rendered text of what it is given. An append is therefore the original text plus the re-write, returned together. A fault that drops the original half **erases the assistant's answer**. The prior system stood in this exact trap: its `replace` mode blanked each streamed part, which forced three separate "show the original again" branches through the file.

**Cost is per text block, not per message.** ADR 0001 accepted "one extra model call for every assistant message". This decision corrects that figure. A message with three qualifying text blocks costs three re-write calls and shows three appended blocks.

**One fact is unsettled and must be measured.** Two sources disagree on whether the harness offers the hook a text block that comes **after** a tool call in the same message. A measurement of the harness says only the first text block is offered. The harness documentation says the hook fires again for text after a tool call. The scope above states the intent — every text block. The seam decision must measure which source is right, and record the gap if the answer is the narrower one.

**A re-write cannot be re-read.** The appended text never enters the transcript, the export, or a resumed session. It survives only in the terminal scrollback.
