# Lessons from the prior system

A critique of an earlier system that rewrites assistant messages into a target style. The
system runs as a sidecar to a coding-agent harness.

## Conventions used here

- The system is "the prior system".
- Its environment variables all share one project-name prefix. This document writes that
  prefix as `X_`. So `X_CONTEXT_TURNS` is one setting, `X_MODE` is another.
- Commits are named by the gist of their message, not by identifier.
- File paths are repository-relative.

## Shape of the prior system

Two shell scripts, no build step, no tests, no CI:

- `rewrite.sh` (361 lines) — a `MessageDisplay` hook. The harness fires this event once per
  streamed chunk of an assistant message. Each fire is a new process. The script writes each
  chunk to a temp file, and on the final chunk it reassembles the message, calls a local
  model through an ollama HTTP endpoint, and returns the rewrite as `displayContent`.
- `rewrite-md.sh` (222 lines) — a `PostToolUse` hook on `Write|Edit`. If the written file is
  Markdown under one opted-in directory, the script rewrites the file and writes it to disk.
- `hooks/hooks.json` — the registration, with a 60 s budget for the display hook and 180 s for
  the Markdown hook.
- `README.md` (392 lines) — larger than either script.

The dependency set is `bash`, `jq`, `curl`, and a local model runtime. All configuration is
environment variables. All state is files in `$TMPDIR`.

---

## Evolution

Ten decisions that the history shows being reversed or reworked.

### 1. What context goes in the prompt — three designs in three days

- **Start.** The first release sent the last user message only. One `jq` expression, one line:
  `[ .[] | select(.type=="user" ...) | .message.content ] | last // "" | .[0:800]`.
- **Second design.** The commit that sends recent conversation instead of the last question
  replaced that line with a 30-line `jq` program: the last N user/assistant messages, merged by
  `.message.id`, with thinking, tool-use, tool-result, sidechain, and meta lines dropped. The
  same commit added a patch for its own new failure — `X_CONTEXT_KEEP_USER`, which re-adds
  the newest user message "when the recent window holds no user message (long tool runs push
  it out)".
- **Third design.** The next commit, the following morning, anchored the excerpt on the
  user's question. Its message states the reason plainly: "A flat last-N-messages window breaks
  on an agentic turn: tool-call status lines fill it and push the question out. Anchoring on the
  question fixes that without a special case, so `X_CONTEXT_KEEP_USER` is gone." The diff
  deletes the flag added the day before and grows the `jq` program to ~57 lines, with an
  exchange model (`group_by`, `foreach`, a `render` function) and per-exchange compression.

The lesson is in the shape, not the outcome. A flat message window is the obvious design and it
is wrong, because an agentic turn is not a chat turn. The unit that survived is the **exchange**
(one user message to the next), not the message.

### 2. Default model — from too small to too large

The first release defaulted to a 3B model. The commit that changes the default records the
result: "its default model was [a 3B model] (not installed), so ollama returned 'model not found'
and the rewrite was skipped with no indication." The new default is a 26B model, about 17 GB,
about 60 tokens/s on the author's machine.

That single choice set the rest of the timeout architecture. The same commit split one timeout
into two (`X_TIMEOUT` 45 s for display, `X_MD_TIMEOUT` 150 s for files) and raised the
Markdown hook's registered budget from 60 s to 180 s.

### 3. Failure signalling — from silent to three-way classified

- **Start.** Pure fail-open. Nothing on screen when the model was down.
- **First fix.** A commit adds a once-per-session notice for one cause only: the endpoint
  unreachable (`curl_rc != 0`). Its comment states the boundary: "A model error while ollama IS
  up (curl_rc=0, empty content) stays silent — a notice would be wrong then."
- **Second fix.** The next release widened it, because the boundary was wrong. The condition
  became `[ "$curl_rc" != "0" ] || [ -n "${err:-}" ]`, and the notice text branches four ways:
  timeout (`curl_rc = 28`), unreachable, model not pulled (`grep -qi 'not found'` on the error
  body), and other error. A later contributor commit fixed the stale comment that the first
  design left behind.

Fail-open and diagnosability pulled against each other for three commits. The final answer is a
one-line append that never suppresses content (`rewrite.sh:332`), plus a per-session marker file
so it appears once.

### 4. Enable and disable — env, then a flag file, then a command

`X_ENABLED` is read once at process start, and the harness freezes the environment at
session launch. A contributed commit adds a flag file that both hooks check on every invocation
(`rewrite.sh:71`, `rewrite-md.sh:55`), with the reason in the comment: "env is frozen at session
launch, so a hotkey or script can't flip `X_ENABLED` mid-session. A flag file can be checked
fresh on every invocation." The line that fixed it is `[ -f "$OFF_FILE" ] && ENABLED=0`.

A later version of the same codebase went one step further and added a slash command with a
persisted override store and a provenance dashboard, which shows where each value came from.
The env-only configuration model did not survive contact with users.

### 5. Markdown assembly order — marker first, then frontmatter first

The first release assembled the overwritten file as marker, then frontmatter, then body. A
contributed fix records the consequence: "Frontmatter only counts as frontmatter on line 1, so
every parser stopped seeing it." The fix moves the marker after the frontmatter, which then
forces two more changes in the same commit: the frontmatter split must now run **before** the
idempotency check, and the check must accept two layouts, because files written by the previous
version have the marker on line 1. `rewrite-md.sh:147` still carries both:
`if [ "$first_line" = "$MARKER" ] || [ "$body_first" = "$MARKER" ]`.

### 6. Temp-file cleanup — a sweep that did not match what it made

The first release swept `-mindepth 2 -maxdepth 2 -type d`. The same release wrote *files* named
`$sid.$mid.out`, `.orig`, and `.notice`. The contributed fix states the result: "the display hook
leaked one temp file per assistant message". `emit()` now deletes the file it just read
(`rewrite.sh:110`), and a second `find` removes empty session directories.

The fix is incomplete, and the incompleteness is visible in the same code. See Strain points.

### 7. Hook command quoting

A one-line contributed fix quotes `"${CLAUDE_PLUGIN_ROOT}"` in `hooks/hooks.json`. The failure it
removes is the worst kind for this design: on a path with a space, the shell word-splits, the
hook execs the wrong binary, and "silently never runs" — indistinguishable from fail-open.

### 8. Version number — bumped for cache, then unbumped for provenance

Two commits, two hours apart. The first bumps to `0.2.0` with the reason: "The display hook
prompt changed shape, and the installer keys its cache by version — 0.1.1 kept serving the old
`rewrite.sh`." The second replaces `0.2.0` with a pre-release suffix on the older number, so that
the version can never be read as a release of the line the code came from.

One field is being asked to carry two unrelated meanings — cache identity and provenance — and
the second commit chose provenance while leaving the cache problem that caused the first bump.

### 9. A prompt-mechanism claim, asserted and then withdrawn

The commit that adds the project-glossary block also asserted a mechanism: the closing
instruction "must go last", because higher up the model "rewrote the nearest message in the
conversation excerpt instead of the message on screen, in every run". Three commits later, the
commit that withdraws the claim states what "every run" meant: "That came from two runs, one per
placement, at temperature 0.3. It does not reproduce. Twenty runs — five per placement, across
two message bodies, one variable changed — rewrote the correct message every time." The code
comment and the README paragraph were both cut back. The commit closes: "What caused the two
original failures is unknown."

This is the most useful commit in the history. The system has no evaluation harness, so a
two-sample observation became a documented mechanism, and only a deliberate re-test removed it.

### 10. Install instructions that did not resolve

An issue reports that the README's first install path names a community catalog that does not
contain the plugin: "no entry named ... and no occurrence of the string ... anywhere in the file."
A commit re-orders the paths. A later commit fixes the same class of error again: the Install
section still named the wrong source, so anyone who followed the README installed a different
build than the one the README described.

---

## Load-bearing choices

### Held up

**The fail-open contract.** This is the strongest decision in the system, and it is stated as a
contract at the head of both files: "on ANY problem (disabled, no jq, parse error, LLM down,
timeout, empty rewrite) we emit nothing and exit 0, which leaves the ORIGINAL text on screen. A
display hook must never be able to swallow the assistant's answer." Every branch honours it. Every
new feature is measured against it — the notice commit argues explicitly that appending a line
"never suppresses content, so fail-open still holds", and the file hook restates it as "never
writes a partial or empty rewrite over real content". Eighteen commits later the contract is intact.
It is also why the system is safe to run on real work despite having no tests.

**Display-only.** The rewrite changes rendered text and nothing else. The transcript and the
agent's own context keep the original. This bounds the blast radius of a bad rewrite to one
screen, which is what makes a small local model an acceptable component.

**Buffer-to-final keyed by message id.** The harness fires per chunk; the model needs the whole
message. Writing `$idx.part` files under `$TMPDIR/<session>/<message>/` and acting only on
`.final` is the correct minimal answer to that mismatch, and it did not change once in the
history. It has a price, paid in full: see Unresolved problems.

**Opt-in by directory for the file-writing hook.** The one hook that changes bytes on disk does
nothing until a directory is named, and re-checks the resolved absolute path against that
directory (`rewrite-md.sh:107-114`). The safe default for a destructive feature is off.

### Did not hold up

**Configuration by environment variable only.** Broken within a day by "I want to turn this off
right now", and patched with a flag file. See Evolution 4.

**One local runtime, hard-coded.** The endpoint, the request shape (`/api/chat`,
`stream:false`, `think:false`, `temperature:0.3`, `rewrite.sh:297-301`), and the response path
(`.message.content`) are inlined in both scripts. Users asked for the constraint to be lifted —
one issue is only the sentence "Would love to try this if it didn't need [the runtime]." A later
version of the same codebase extracted a shared provider module for exactly this reason.

**Two scripts, one prefix, no shared code.** The two hooks duplicate config parsing, the prose
length gate, the curl call, the error classification, and the notice logic. They have already
drifted: `rewrite.sh:87-91` validates numeric env vars before passing them to `jq --argjson`;
`rewrite-md.sh` has no such validation. The display hook appends its notice to the screen; the
file hook emits a `systemMessage`. The two use different timeout variables with a 3.3x gap. The later
provider extraction states the motive directly — the hooks share a module "so they can't drift".

**Shell plus `jq` as the whole toolchain.** This bought a zero-install plugin. It stopped paying
when the context extractor reached ~57 lines of embedded `jq` with its own helper functions
(`rewrite.sh:231-287`), including a comment for a language footgun: `# .[-0:] is .[0:], so 0
needs its own branch`. That program is the highest-risk logic in the system and it cannot be run,
tested, or debugged apart from a live hook fire.

---

## Strain points

**`replace` mode forces three "re-show the original" branches.** Because the mode blanks every
streamed chunk (`emit_empty`, `rewrite.sh:153`), every early exit must reconstruct and re-emit
the whole message. The pattern `out="$mdir.orig"; printf '%s' "$full" > "$out" ... && emit "$out"`
appears at `rewrite.sh:175`, `:299`, and `:345`. The README labels the mode "Experimental". One
display strategy is responsible for most of the branching in the file.

**The temp-file leak is only partly fixed.** The sweep at `rewrite.sh:139-140` matches `-type d`
in both passes. The per-session notice markers are *files*: `$BUF_ROOT/$sid.notified`
(`rewrite.sh:319`) and `$LOG_ROOT/$SID.md-notified` (`rewrite-md.sh:184`). Nothing ever removes
them. The debug log at `rewrite.sh:98` is appended to and never rotated.

**About ten processes per streamed chunk.** `rewrite.sh:127-132` runs six separate
`printf | jq` pipelines to read six fields out of one JSON payload, then two `find` commands, a
`mkdir`, and one more `jq` to persist the delta — on every chunk of every message, whether or not
a rewrite will ever happen. No measurement of this cost exists anywhere in the repository.

**The length gate counts bytes and calls them characters.** `tr -d '[:space:]' | wc -c`
(`rewrite.sh:161-163`, `rewrite-md.sh:152-154`) is documented as "non-space chars". For
non-ASCII prose the gate triggers early.

**The gate skips exactly the messages most worth rewriting.** `X_MIN_CHARS` defaults to 200
characters of prose with fenced code stripped. Short answers are the densest in jargon and are
never rewritten.

**Code-block preservation is a request, not a mechanism.** The prompt says "Leave fenced code
blocks unchanged" (`rewrite.sh:189`) and, for files, "Do NOT change fenced code blocks or any
YAML frontmatter; reproduce them exactly" (`rewrite-md.sh:166`). Nothing verifies the output. The
fence detector itself is a toggle — `awk 'BEGIN{f=0} /^```/{f=!f; next}'` — which miscounts on an
unbalanced or indented fence.

**Two competing instructions at the end of the prompt.** `rewrite.sh:290-294` appends "Use the
material above only to understand the message. Do NOT rewrite, answer, or repeat any of it", and
then appends a second framing that addresses the model as if the user had just spoken. The
withdrawal commit (Evolution 9) shows the author was not sure how these interact and could not
establish it by experiment.

**Backward compatibility already carried in a 0.1.x prototype.** `rewrite-md.sh:147` accepts two
marker layouts to avoid re-chewing files written by an earlier version, in a project the README
calls a "working prototype".

**No tests, no CI, no lint config.** The only test affordance is `X_STUB`, which substitutes a
fixed string for the model. It tests display mechanics. It cannot test the context extractor, the
frontmatter split, or the rewrite quality that is the product.

---

## Unresolved problems

**The rendering path was not verified before the design was built on it.** Two long issue
threads report that the display block never appears in the interactive interface, on a harness
version where the feature exists.

- The first is still open. Its author ran with the deterministic stub and the debug log, showed
  the hook emitting well-formed output on every final chunk, showed the same output honoured in
  the non-interactive print mode, and concluded that every interactive renderer drops it. A
  second user reproduced that split. The maintainer could not reproduce it at all, on the same
  harness version and the same terminal.
- The second thread built a minimal reproduction with a trivial hook that had nothing to do with
  this system, and concluded: "Its entire purpose is the interactive TUI, which is exactly the
  mode where [the harness] currently drops `displayContent`." Its author then retracted it. The
  real cause was a `verbose: true` setting in their own config, which is documented to bypass
  `displayContent` and render the original.

So the mechanism does work. The point is the cost of finding that out. Four people, two
long threads, and several days went into a question the system could not answer about itself:
was my output rendered, and if not, why not? The system emits and exits. It never learns the
answer, so it can never tell the user.

**Latency is structural and unpriced.** The rewrite cannot start until the message is complete,
then costs a full model call. Measured in the repository: 5 s for a 4000-character glossary
excerpt, 8 s at 12000, 13 s for a 29 KB file, and 11 s for a warm run with the full conversation
excerpt. In `append` mode the block arrives after the answer. In `replace` mode the screen shows
nothing at all while the message streams, then the whole rewrite appears at once. The design
converts a streaming interface into a batch one.

**Every message re-sends everything.** The glossary file is read and re-sent on every assistant
message (`rewrite.sh:196-204`). The conversation excerpt is rebuilt from the transcript every
time. There is no caching, no reuse, no `keep_alive`, and no token budget — only three separate
character caps (800 per message, 4000 for the glossary, N exchanges). Nothing checks the total
against the model's context window.

**Two hooks, one local runtime, no coordination.** The file hook may hold the runtime for up to
150 s. The display hook allows 45 s. A file rewrite in flight can time out every display rewrite
behind it. Nothing detects or reports this.

**The file hook blocks the agent loop.** It is registered with a 180 s budget on `Write|Edit`. In
the worst case the agent waits over two minutes after writing a file, per write, with no debounce
across repeated edits to the same file.

**Overwrite mode makes the agent's view of the file wrong.** The hook replaces bytes the agent
just wrote, while the agent's context still holds the original text. A later exact-match edit to
that file will fail. Nothing in the code or the README addresses this; the README only warns that
"A weak model can degrade real docs — use with care". In `sibling` mode no marker is written, so
every subsequent edit re-runs a whole-file model call.

**The transcript format is a private interface.** The extractor depends on `.type`, `.isMeta`,
`.isSidechain`, `.message.id`, and the block shape of `.message.content`. If any of these change,
`jq` returns empty, the context block silently disappears, and the rewrite quietly degrades.
Fail-open hides the regression: there is no notice for "context extraction produced nothing",
only for endpoint failures.

**Partial and abandoned messages.** If the final chunk never arrives — interrupt, crash, hook
killed at the 60 s budget — the buffer directory remains until an opportunistic 30-minute sweep.
Nothing re-shows or reconciles the partial message.

**Style and language are hard-coded.** The prompt fixes both the target register and English
(`rewrite.sh:189`, `:206`). A later version of the same codebase had to add language-following
and user-supplied prompt files, which is the strongest evidence that "one prompt, one style" was
too narrow.

**Version is overloaded.** The installer caches by version; provenance also wants that field.
The system chose provenance and settled on a version that sorts *below* the one it published
first, so a user who installed the higher number may never receive the update.

---

## Open questions for a redesign

**Rendering and placement**

1. How does the rewriter learn whether its output was actually displayed, rather than assuming it
   was, and what should it do when the answer is no?
2. Which harness modes and settings can silently discard the rewrite, and should the system detect
   them at startup and say so once, instead of leaving each user to reproduce the same
   investigation?
3. Is replacing rendered text the right seam at all, or should the rewrite live somewhere it can
   be re-read, copied, and referenced later — a panel, a file, a command?

**Streaming and latency**

4. Can a rewrite be streamed as the original streams, or is whole-message input a hard
   requirement of quality? What does the interface look like if the answer is "partly" — for
   example, per-paragraph rewrites that land as the paragraphs complete?
5. What is the acceptable delay before a rewrite is worse than no rewrite, and what does the
   system do when it predicts it will exceed that budget before it starts?
6. If the original text is suppressed while the rewrite is produced, what does the user see in
   the gap, and who is responsible for restoring the original if the rewrite never arrives?

**What the rewriter is told**

7. What is the right unit of conversation history for an agentic session — the message, the
   exchange, or the tool-free summary of a turn — and which unit stays correct when one user
   question produces forty assistant messages?
8. Which of the context inputs actually improve the rewrite? The prior system asserted the value
   of a project glossary from one comparison and the value of prompt ordering from two runs, then
   had to withdraw the second. What experiment design would settle these before they become
   documented mechanisms?
9. Should the project vocabulary be re-sent on every single message, or extracted once per
   session, cached, and reduced to the terms that appear in the message being rewritten?
10. How is the total prompt budgeted against a real context window, rather than by three
    independent character caps that can sum past it?

**Failure, verification, and trust**

11. Fail-open is clearly right. But what is the equivalent for *silent degradation* — a context
    extractor that starts returning nothing, or a model that returns fluent text that dropped a
    number? What can be checked cheaply on every rewrite: preserved code blocks, preserved
    numbers, preserved file paths, length ratio?
12. Should a rewrite that fails a check be shown with a warning, shown at all, or discarded?
13. How does the system distinguish "the user turned it off", "the model is missing", "the
    runtime is busy", and "the harness dropped my output" — all of which look identical to the
    user today?

**Cost, contention, and scope**

14. What is the cost model per session — calls, tokens, seconds, watts — and does the design let
    a user see it before they enable it on every message?
15. When one local runtime serves several concurrent callers, who queues, who is dropped, and
    what tells the user that a rewrite was skipped because something else held the model?
16. Should any part of the rewriter run inside the agent's blocking loop? If a file rewrite takes
    two minutes, what is the argument for making the agent wait rather than doing the work out of
    band?
17. Should the rewriter ever write bytes the agent believes it wrote itself, and if so, how is the
    agent's view of that file corrected?

**Configuration and control**

18. What is the smallest control surface that answers "off, right now, in this running session"
    and "different for this project" without three mechanisms (env, flag file, command) that each
    know a different subset of state?
19. Where does the state of a runtime override live, who owns its precedence, and how does the
    user see which layer supplied each value?
20. Is one prompt and one target style the product, or is the product the pipeline, with style,
    language, and audience as inputs? The prior system started at one style in English and had
    to add both later.

**Structure**

21. Where is the seam between "talk to a model" and "decide what to rewrite"? The prior system
    had none, duplicated both hooks, and drifted within days. What is the smallest shared core
    that makes drift impossible?
22. What is the correct language for the extraction logic? A ~57-line embedded `jq` program was
    the highest-risk code in the prior system and the only part that could not be run in
    isolation.
23. What is the minimum test that would have caught each fixed defect here — frontmatter ordering,
    the leaked temp files, the unquoted path, the missing default model? All four were reachable
    by a test that runs a hook against a fixed payload and inspects the result.
