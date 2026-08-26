# Harness attachment points

Every way a process outside the main agent loop can put text on a Claude Code
user's screen, or change text that is already on its way there.

This document is a seam catalogue. A design that must rewrite assistant messages
into a different style has to pick one of these seams. The catalogue exists so
the choice is made against the full list.

---

## Conventions used here

- **The harness** is the Claude Code CLI.
- **The sidecar** is the process that wants to change what the user sees.
- **The screen** is the interactive terminal interface, unless the text says
  otherwise. Print mode and the SDK are called out by name, because they behave
  differently.
- Machine-specific paths are written in a neutral form. `~/.claude/` is the
  user-level configuration directory. `<cli>` is the installed CLI binary.

---

## Sources

Every claim below comes from one of these. The claim says which one.

| Tag | Source | Version / date |
|---|---|---|
| `[docs]` | Official documentation on `code.claude.com/docs/en/*` (the `docs.claude.com/en/docs/claude-code/*` paths redirect here) | Fetched 2026-08-26 |
| `[cli]` | `<cli> --help` on the installed binary | 2.1.246 |
| `[bin]` | Strings and code extracted from the installed CLI binary | 2.1.246, build `2026-08-25T18:33:51Z`, git sha `1ba9d2211ae14e591bd1d60451c217c51f415e86` |
| `[test]` | Measured by running the installed CLI against a purpose-built hook | 2.1.246, run 2026-08-26 |
| `[sdk]` | Claude Agent SDK documentation on `code.claude.com/docs/en/agent-sdk/*` | Fetched 2026-08-26 |

`[bin]` and `[test]` are stronger than `[docs]` where they disagree, because
they are the behaviour of the version the user runs. They are also the most
perishable. Re-measure before you trust this document against a newer build.

---

## The eight questions

Every attachment point below is answered against these.

1. **Name and trigger.** What is it, and what interface or event fires it?
2. **Cadence.** When does it fire, and how many times per assistant message?
3. **Input shape.** What data does it receive? A real payload, quoted.
4. **Authority.** What is it permitted to change?
5. **Delivery guarantee.** Is the change guaranteed to reach the screen, and
   which settings or modes discard it silently? *This is the question that
   matters most.*
6. **Acknowledgement.** Can the sidecar confirm its output was displayed?
7. **Budget.** What is its time budget, and does it block the agent?
8. **Persistence.** Can the output be re-read, copied, or referenced after it
   scrolls away?

---

## Executive summary

There is exactly one seam that rewrites assistant prose before it is rendered:
the **`MessageDisplay`** hook. Every other seam either writes *beside* the
assistant message, writes *into the model's context*, or owns the whole
rendering surface itself.

Three facts about `MessageDisplay` decide most designs:

1. Its default time budget is **10 seconds**, not the 600 seconds that other
   command hooks get. `[bin]` `[test]`
2. In the interactive interface, the `verbose` setting **silently discards** the
   rewrite and renders the original. `[bin]`
3. In print mode and the SDK, the rewrite is **not display-only**. It replaces
   the text in the emitted assistant message and in the result. The transcript
   still keeps the original. `[test]`

Fact 2 is the failure a prior design hit. It is a one-line condition in the
renderer, and nothing tells the sidecar that it happened.

---

## Family A — Hook events

### A.0 The event list

The installed 2.1.246 binary carries a registry of **31 hook events**. `[bin]`
This is the whole list, with the registry's own one-line summary:

| Event | Summary (verbatim from the binary) |
|---|---|
| `PreToolUse` | Before tool execution |
| `PostToolUse` | After tool execution |
| `PostToolUseFailure` | After tool execution fails |
| `PostToolBatch` | After a batch of tool calls resolves |
| `PermissionRequest` | When a permission dialog is displayed |
| `PermissionDenied` | After auto mode classifier denies a tool call |
| `Notification` | When notifications are sent |
| `UserPromptSubmit` | When the user submits a prompt |
| `UserPromptExpansion` | When a user-typed slash command expands into a prompt |
| `SessionStart` | When a new session is started |
| `SessionEnd` | When a session is ending |
| `Setup` | Repo setup hooks for init and maintenance |
| `Stop` | Right before Claude concludes its response |
| `StopFailure` | When the turn ends due to an API error |
| `SubagentStart` | When a subagent (Agent tool call) is started |
| `SubagentStop` | Right before a subagent (Agent tool call) concludes its response |
| `PreCompact` | Before conversation compaction |
| `PostCompact` | After conversation compaction |
| `TeammateIdle` | When a teammate is about to go idle |
| `TaskCreated` | When a task is being created |
| `TaskCompleted` | When a task is being marked as completed |
| `Elicitation` | When an MCP server requests user input (elicitation) |
| `ElicitationResult` | After a user responds to an MCP elicitation |
| `ConfigChange` | When configuration files change during a session |
| `InstructionsLoaded` | When an instruction file (CLAUDE.md or rule) is loaded |
| `CwdChanged` | After the working directory changes |
| `DirectoryAdded` | After a working directory is added mid-session |
| `FileChanged` | When a watched file changes |
| `WorktreeCreate` | Create an isolated worktree for VCS-agnostic isolation |
| `WorktreeRemove` | Remove a previously created worktree |
| `MessageDisplay` | While assistant message text is displayed |

**Only `MessageDisplay` sees assistant prose and can change it before it is
rendered.** `Stop`, `StopFailure` and `SubagentStop` also *see* assistant text,
in a `last_assistant_message` field, but the text is already on screen by then
and they cannot replace it. `PostToolUse` can replace **tool output**, never
assistant prose. `[docs]` `[bin]`

### A.1 The common output envelope

Every hook may return one JSON object on stdout. The envelope is the same for
all events. `[bin]`

```
{
  continue?: boolean,
  suppressOutput?: boolean,
  stopReason?: string,
  decision?: "approve" | "block",
  systemMessage?: string,
  terminalSequence?: string,
  reason?: string,
  hookSpecificOutput?: { hookEventName: <event>, ...event-specific fields }
}
```

| Field | What it does |
|---|---|
| `continue` | `false` stops the harness after the hook runs. It beats every event-specific decision. `[docs]` |
| `stopReason` | Shown to the user when `continue` is `false`. Not shown to the model. `[docs]` |
| `suppressOutput` | **Dead field.** The harness accepts it and does nothing with it. A successful hook's stdout is never in the transcript anyway. `[docs]` |
| `systemMessage` | A warning line shown to the user. Discarded in many modes — see A.3. `[docs]` |
| `terminalSequence` | A terminal escape sequence the harness emits for the hook. Only OSC 0, 1, 2, 9, 99, 777 and BEL pass; anything else is dropped. Ignored in print mode and the SDK. `[bin]` `[docs]` |
| `reason` | The blocking reason, on events that can block. `[docs]` |
| `hookSpecificOutput` | The per-event payload. `MessageDisplay` puts `displayContent` here. `[bin]` |

An async variant exists: `{ "async": true, "asyncTimeout"?: number }`. An async
hook runs in the background, cannot block, and **its `systemMessage` is never
shown to the user**. `[bin]` `[docs]`

Parsing rule: the harness decides JSON against plain text by the first
non-whitespace byte. `{` means JSON. Anything else — including a JSON array or a
quoted JSON string — is plain text. `[docs]`

Size cap: every hook output string, `additionalContext` and `systemMessage`
included, is capped at 10 000 characters. Longer output is written to a file and
replaced with a preview plus the path. `[docs]`

### A.2 Exit-code behaviour

| Exit code | Effect |
|---|---|
| 0 | stdout goes to the debug log only, for most events. The exceptions — `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart` — add plain stdout to the **model's** context. stderr goes to the debug log only. `[docs]` |
| 2 | Blocking error, on events that can block. The message is the JSON reason if present, else stderr. `[docs]` |
| other non-zero | With valid JSON, the exit code is ignored and the JSON decides. With invalid or plain-text stdout, a non-blocking error notice appears in the transcript. **Exit code 1 does not block.** `[docs]` |

`MessageDisplay` is special: any non-zero exit code simply displays the original
delta. It cannot block. `[bin]`

### A.3 Where hook text is discarded

This is the answer to question 5 for the whole hook family. Nothing a hook
prints is guaranteed to reach the screen.

| Discard mechanism | What it kills |
|---|---|
| `verbose` true (setting, `--verbose`, or `/config`) | The `MessageDisplay` rewrite. The original renders. `[bin]` |
| `--output-format text` (the `-p` default) | `systemMessage`. `[docs]` |
| `--output-format json` | `systemMessage`. `[docs]` |
| Print mode and the SDK, any format | `terminalSequence`. `[docs]` |
| `"async": true` | `systemMessage`, and every decision field. `[docs]` |
| `disableAllHooks: true` (managed policy) | Every command hook. The debug log says `Policy disableAllHooks: skipping configured hooks`. SDK callback hooks still run. `[bin]` |
| `allowManagedHooksOnly` | User, project, local and plugin hooks. `[docs]` |
| Workspace trust not accepted | Settings-file hooks, until the trust dialog is accepted. `[docs]` |
| `--safe-mode` | Customizations, hooks included. `[cli]` |
| `--bare` | Hooks, LSP, plugin sync, auto-memory, CLAUDE.md auto-discovery. `[cli]` |
| Timeout | The whole hook response. `[docs]` |
| Exit 0, any mode | stdout and stderr, for most events. Debug log only. `[docs]` |

Twelve events discard `systemMessage` outright, whatever the mode:
`Notification`, `StopFailure`, `MessageDisplay`, `ConfigChange`, `PreCompact`,
`PostCompact`, `SessionEnd`, `InstructionsLoaded`, `WorktreeCreate`,
`WorktreeRemove`, `Elicitation`, `ElicitationResult`. `[docs]`

### A.4 `MessageDisplay` — the only prose-rewriting seam

**1. Name and trigger.** `MessageDisplay`. The harness fires it while assistant
message text is displayed. It has no matcher. `[bin]`

**2. Cadence.** Two different cadences, and the difference is load-bearing.

*Interactive interface.* The harness buffers the streamed text and flushes on
whole completed lines. `[bin]` The flush machinery has three constants:

| Constant | Value | Meaning |
|---|---|---|
| flush rate | 10 per second | A flush happens at most every 100 ms |
| in-flight cap | 3 | No new flush is dispatched while 3 hook processes are running |
| default budget | 10 000 ms | Passed to the hook dispatcher for this event |

A non-final flush cuts the buffer at the **last newline**. The final flush takes
whatever is left. So the sidecar receives whole lines, not arbitrary chunks, and
the count per message is *one or more* — it depends on how many line breaks the
message has and how fast it streams. `[bin]`

*Print mode and the SDK.* One fire per assistant message that contains text,
after the message is complete, with `index: 0`, `final: true`, and `delta`
holding the whole message. `[bin]` `[test]`

In both modes, an assistant message with no text — a pure tool-call message —
fires nothing. The dispatcher returns early when the concatenated text is empty.
`[bin]` `[test]`

**3. Input shape.** Measured verbatim from the installed 2.1.246, print mode.
Paths are neutralised.

```json
{
  "session_id": "d7d436df-2a7c-4b8b-a380-62cb60fc5efd",
  "transcript_path": "~/.claude/projects/<project-slug>/d7d436df-2a7c-4b8b-a380-62cb60fc5efd.jsonl",
  "cwd": "<working directory>",
  "prompt_id": "1ec83c84-dadf-4252-bebc-b7fcb2c21763",
  "hook_event_name": "MessageDisplay",
  "turn_id": "1903dbc4-ed31-425e-af84-bcc3cf9e16d0",
  "message_id": "fd925c0c-5d93-4896-a5eb-12367436ac97",
  "index": 0,
  "final": true,
  "delta": "hello world one two three"
}
```

`[test]`

Two field facts that a design must respect:

- There is **no `permission_mode` field** and **no `effort` field** on this
  event. Other events carry them. `[test]`
- `message_id` groups the flushes of one message, but it is **not** the API
  message id. It cannot be joined against transcript entries. `[docs]`
- In the interactive interface the final flush's `delta` is **empty** when the
  message ends on a newline. Use `final`, never a non-empty `delta`, as the
  end-of-message signal. `[docs]`

**4. Authority.** One field, in `hookSpecificOutput`:

```json
{"hookSpecificOutput":{"hookEventName":"MessageDisplay","displayContent":"..."}}
```

`displayContent` replaces what this flush renders. Omitting it leaves the flush
alone. An empty string blanks the flush. The binary's own schema note:
`"Text displayed in place of the delta. Omit (or return the delta unchanged) to
display the original."` `[bin]`

The per-flush results are concatenated **in order** to build the displayed
message, even though the hook processes run in parallel. `[bin]`

`systemMessage` and `continue` are discarded on this event. `[docs]`

**5. Delivery guarantee.** This is where a prior design failed, so it is set out
in full.

*Interactive interface.* The renderer holds the rewrite in a display-layer store
keyed by the API message id, separate from the transcript. The render condition
is, in effect:

```
if (rewrite !== undefined && !verbose) {
    if (!isFirstTextBlock) return null;   // later text blocks are hidden
    render the rewrite
} else {
    render the original
}
```

`[bin]` Three consequences:

- **`verbose` truthy discards the rewrite silently.** The original renders.
  Nothing is logged to the session. This is the exact condition a prior design
  spent several days and two issue threads failing to identify.
- Only the **first** text block of the message shows the rewrite. Later text
  blocks in the same message render as nothing.
- While the message is still streaming, a live preview shows only what the hook
  has returned so far. With a `MessageDisplay` hook installed and a rewrite that
  arrives at the end, the screen shows **nothing** while the message streams.
  `[bin]`

*Print mode and the SDK.* The rewrite reaches the consumer on every output
format measured:

| Path | Content | Evidence |
|---|---|---|
| `-p --output-format text` on stdout | rewrite | `[test]` |
| `-p --output-format json`, `.result` | rewrite | `[test]` |
| `-p --output-format stream-json`, the `assistant` message and the `result` | rewrite | `[test]` |
| The session transcript `.jsonl` | **original** | `[test]` |
| What the model sees on the next turn | **original** | `[docs]` |

`--verbose` did **not** suppress the rewrite in print mode. `verbose` is a
rendering flag for the interactive interface. `[test]`

So the label "display-only" is true of the interactive interface and **false**
of print mode and the SDK, where the rewrite becomes the program's answer.

Everything in A.3 also applies: `disableAllHooks`, `allowManagedHooksOnly`,
untrusted workspace, `--safe-mode` and `--bare` all remove the hook entirely.

**6. Acknowledgement.** **No.** There is no acknowledgement channel. The hook
writes to stdout and exits. It receives nothing back. `[docs]`

The only indirect signals:

- The debug log at `~/.claude/debug/<session-id>.txt`, or the path given to
  `--debug-file`. It records which hooks matched, their exit codes, and their
  full stdout and stderr. `[docs]`
- A later flush with a higher `index` for the same `message_id` proves the
  earlier flush was processed — but not that it was rendered. `[docs]`

Nothing tells the sidecar that `verbose` was on. **This is the single largest
gap in the seam.**

**7. Budget.** Default **10 seconds**, not the 600 seconds other command hooks
get. Measured by bracketing:

| Hook sleep | `timeout` field | Result |
|---|---|---|
| 8 s | none | rewrite displayed |
| 11 s | none | original displayed |
| 15 s | none | original displayed |
| 20 s | `60` | rewrite displayed |

`[test]` The constant in the binary is `1e4` ms, which matches. `[bin]`

A per-hook `timeout` field, in seconds, raises the budget and is honoured.
`[test]`

The hook **blocks**: the harness holds each flush until the hook returns.
`[docs]` The in-flight cap of 3 provides backpressure rather than unbounded
queueing. `[bin]`

Handler types accepted: `command`, `http`, `mcp_tool`. **Not** `prompt` or
`agent`. `[docs]` For a sidecar that must answer inside 10 seconds, `http`
against a long-lived local process avoids a process spawn per flush.

**8. Persistence.** **No.** The rewrite is never written to the transcript. It
lives in an in-memory display store that is pruned when its message leaves the
conversation. `[bin]` `[test]` Transcript view (`ctrl+o`), `--resume`,
`--continue` and `/export` all show the original. The rewrite is lost when the
session ends.

### A.5 The near-miss hooks

These see assistant text or write beside it. None can rewrite it.

| Hook | What it sees | What it can put on screen | Verdict |
|---|---|---|---|
| `Stop` | `last_assistant_message`, the completed final text | `systemMessage` (interactive and `stream-json` only), `stopReason` with `continue:false`, `terminalSequence`. `additionalContext` goes to the **model**, not the user, and reopens the turn | Too late. The text is already rendered. Blocking makes the model write **more**, which is the opposite of a rewrite. Does not fire on user interrupt or API error |
| `StopFailure` | The API error string in `last_assistant_message` | `terminalSequence` only. All other output and the exit code are ignored | Useless for display |
| `SubagentStop` | The subagent's `last_assistant_message` | Feedback to the **subagent**, not the parent user | Wrong audience |
| `PostToolUse` | Tool input and response | `updatedToolOutput` replaces the tool result **as the model sees it**; `additionalContext` goes to the model | Rewrites tool output, never prose. The prior system used this seam for Markdown **files** on disk |
| `UserPromptSubmit` | The user's prompt text | stdout is added to the **model's** context | Wrong direction |
| `SessionStart` | Session source | stdout and `additionalContext` reach the **model** | Wrong direction |
| `Notification` | Notification message and type | `terminalSequence` only; `systemMessage` and `continue` are discarded | A notification channel, not a text channel |
| `PostCompact` | The compaction summary | Exit 0 stdout is **shown to the user** | A real user-visible channel, but it fires once per compaction, not per message |

`PostCompact` is worth naming because it is one of the very few events whose
exit-0 stdout is documented as *shown to the user* rather than shown to the
model. `[bin]` It is not a per-message seam.

### A.6 Where hooks are configured

| Location | Scope |
|---|---|
| `~/.claude/settings.json` | The user, all projects |
| `.claude/settings.json` | One project, committable |
| `.claude/settings.local.json` | One project, not committed |
| Managed policy settings | Organisation-wide, admin-controlled |
| A plugin's `hooks/hooks.json` | While the plugin is enabled |
| Skill frontmatter | The rest of the session, once the skill runs |
| Subagent frontmatter | While that subagent runs |

`[docs]` Entries **merge** across levels. They do not replace each other.

Shape:

```json
{
  "hooks": {
    "MessageDisplay": [
      {
        "hooks": [
          { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/rewrite.sh", "timeout": 60 }
        ]
      }
    ]
  }
}
```

Matcher semantics: `"*"`, `""` or omitted matches all. A value made only of
letters, digits, `_`, `-`, spaces, `,` and `|` is an exact string or a
separated list. Anything else is an **unanchored** JavaScript regular
expression, so `Edit.*` also matches `NotebookEdit`. `[docs]` `MessageDisplay`
has no matcher support; a `matcher` key on it is silently ignored. `[docs]`

Variables substituted into `command` and `args`, and exported to the process:
`${CLAUDE_PROJECT_DIR}`, `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`.
`${CLAUDE_PLUGIN_ROOT}` changes on every plugin update, so it must never be
hard-coded. `[docs]`

`/hooks` opens a read-only browser of what is registered, labelled by source.
There is **no way to disable one hook** while leaving it in the configuration.
`[docs]`

### A.7 Multiple `MessageDisplay` hooks race

All matching hooks run in parallel, and each one receives the **original**
delta, not another hook's output. Hooks do not chain. `[docs]` When two hooks
both return `displayContent`, the docs state **no** precedence rule, and a test
observed the winner change between otherwise identical runs. `[test]`

**Documentation gap, and a real hazard.** A design must ensure that exactly one
`MessageDisplay` hook returns `displayContent`, or the output is
non-deterministic.

---

## Family B — The SDK and headless mode

### B.0 The shape of the question

There are three different things a "program that drives the agent" can be. They
have very different powers, and a design must not confuse them.

| Case | Who owns the screen | Can it rewrite assistant text? |
|---|---|---|
| The driver **is** the user interface | The driver | Yes, without limit. There is no other screen |
| The driver runs `claude -p` and shows the output | The driver | Yes, on its own copy |
| The driver wants to attach to a running interactive session a human started | The harness | **No. No documented route exists** |

The third case is the one that matters for a sidecar, and the answer is a plain
no. The SDK `Query` object has no attach or observe method. `[sdk]` Remote
Control is not a local attach point: it registers with the Anthropic API, routes
through Anthropic servers, and mirrors the terminal for a **person** on
claude.ai or the mobile app. It only starts when a human runs it. `[sdk]`

So the inversion is worth stating: **for rewriting assistant text, the hook can
do something the SDK driver cannot** — reach inside a human's interactive
terminal.

### B.1 Print mode (`claude -p`)

**1. Name and trigger.** `claude -p`, with `--output-format` selecting
`text` (default), `json`, or `stream-json`. `[cli]`

**2. Cadence.** One process per invocation.

**3. Input shape.** For `--output-format stream-json`, the emitted message order
in a measured run was:

```
system/hook_started -> system/hook_response -> system/init -> system/status
-> stream_event x4 -> assistant -> stream_event x3 -> rate_limit_event -> result
```

The assistant text lives at `message.content[].text`:

```json
{"type":"assistant",
 "message":{"model":"claude-opus-5","id":"msg_011Ce…","role":"assistant",
   "content":[{"type":"text","text":"hello world"}],
   "stop_reason":null,"usage":{}},
 "parent_tool_use_id":null,"session_id":"…","uuid":"…",
 "timestamp":"2026-08-26T00:29:56.533Z","request_id":"req_011Ce…"}
```

A partial chunk, with `--include-partial-messages`, carries text at
`event.delta.text`:

```json
{"type":"content_block_delta","index":0,
 "delta":{"type":"text_delta","text":"ello world"}}
```

The result carries text at `.result`:

```json
{"type":"result","subtype":"success","is_error":false,"stop_reason":"end_turn",
 "result":"hello world","session_id":"…","total_cost_usd":0.01195,
 "terminal_reason":"completed","ttft_ms":1528,"duration_ms":1772,"uuid":"…"}
```

`[test]`

**4. Authority.** The driver owns its own stdout. It can transform anything it
reads before showing it.

**5. Delivery guarantee.** Whatever the driver prints, it prints. There is no
harness rendering layer to discard it. Print mode itself writes almost nothing:
a run under a pseudo-terminal produced the answer plus one show-cursor escape
sequence. No interface, no spinner, no status line. `[test]`

What still runs in print mode:

| Feature | Runs under `-p`? |
|---|---|
| Hooks | **Yes**, `MessageDisplay` included. `--bare` skips them |
| MCP servers | Yes |
| Output styles | Yes — they change the system prompt, so they change generation, not rendering |
| Status line | Nothing is drawn, because there is no interface. **Documentation gap:** neither the status-line page nor the headless page states this |
| Slash commands and skills | Yes, expanded from the prompt string. Terminal-only commands are unavailable |

One silent-failure trap that belongs in this catalogue: **settings files that
fail validation are silently ignored under `-p`** — no error dialog is shown.
`[cli]` A sidecar whose hook registration has a typo simply never runs.

**6. Acknowledgement.** Yes, fully. The driver reads its own output.

**7. Budget.** Not blocking. The agent has already finished.

**8. Persistence.** Whatever the driver stores.

### B.2 The SDK `query()` loop

**1. Name and trigger.** `query({ prompt, options })` returns a `Query`, an async
generator of `SDKMessage`. `[sdk]`

**2. Cadence.** One `SDKAssistantMessage` per assistant message. Many
`SDKPartialAssistantMessage` per message when `includePartialMessages` is set.

**3. Input shape.**

```typescript
type SDKAssistantMessage = {
  type: "assistant"; uuid: UUID; session_id: string;
  message: BetaMessage; parent_tool_use_id: string | null;
  error?: SDKAssistantMessageError; aborted?: true;
  timestamp?: string; context_usage?: SDKContextUsage;
};

type SDKPartialAssistantMessage = {
  type: "stream_event"; event: BetaRawMessageStreamEvent;
  parent_tool_use_id: string | null;   // always null - main session only
  uuid: UUID; session_id: string; ttft_ms?: number;
};
```

`[sdk]` The full union has more than 30 members, including
`SDKResultMessage`, `SDKSystemMessage`, `SDKCompactBoundaryMessage`,
`SDKHookResponseMessage` and `SDKInformationalMessage`.

**4. Authority.** Over its own rendering, total. Over the agent, only through
the control protocol (B.3).

**5. Delivery guarantee.** Guaranteed if the driver is the interface. Zero reach
into an interactive session it did not start.

**6. Acknowledgement.** Yes.

**7. Budget.** Not blocking.

**8. Persistence.** The driver's own concern.

### B.3 The control protocol

Methods on the `Query` object that no hook has: `interrupt()`, `setModel()`,
`setPermissionMode()`, `setMaxThinkingTokens()`, `applyFlagSettings()`,
`rewindFiles()`, `stopTask()`, `setMcpServers()`, `toggleMcpServer()`,
`reconnectMcpServer()`, `getContextUsage()`, `readFile()`, `reinitialize()`,
`supportedCommands()`, `supportedModels()`, `supportedAgents()`,
`mcpServerStatus()`, `accountInfo()`, `streamInput()`, `close()`. `[sdk]`

Four of them — `interrupt()`, `setModel()`, `setPermissionMode()` and
`applyFlagSettings()` — work **only in streaming-input mode**, where `prompt` is
an async iterable. `[sdk]`

One documented trap: `applyFlagSettings()` system-prompt keys are resolved once
at startup. The call succeeds mid-session and does nothing. `[sdk]`

None of these change assistant text.

### B.4 `canUseTool`

```typescript
type CanUseTool = (
  toolName: string,
  input: Record<string, unknown>,
  options: { signal: AbortSignal; suggestions?: PermissionUpdate[];
             blockedPath?: string; decisionReason?: string;
             toolUseID: string; agentID?: string; requestId: string }
) => Promise<PermissionResult | null>;
```

`[sdk]` It fires **only when the permission flow resolves to a prompt**. Calls
pre-approved by `allowedTools`, a settings rule, or a mode such as
`acceptEdits` never reach it. To gate every call, use a `PreToolUse` hook
instead. It rewrites tool **input**, never assistant text. Returning `null`
without an out-of-band `control_response` blocks the tool call forever —
permission prompts do not time out. `[sdk]`

### B.5 Programmatic hooks through the SDK

The SDK accepts hooks as in-process callbacks rather than subprocesses:

```typescript
type HookCallback = (input: HookInput, toolUseID: string | undefined,
                     options: { signal: AbortSignal }) => Promise<HookJSONOutput>;
interface HookCallbackMatcher { matcher?: string; hooks: HookCallback[]; timeout?: number }
```

`[sdk]` **Same events, same payloads, no extra powers.** They are faster because
there is no process spawn. `terminalSequence` is explicitly ignored by the SDK.
`[sdk]`

`disableAllHooks` kills command hooks but **not** SDK callback hooks. `[bin]`

A language parity gap worth knowing: the Python SDK's `HookEvent` literal lists
only 10 events and **does not include `MessageDisplay`**. TypeScript has the
full set. A Python driver can still get `MessageDisplay` by registering a
command-type hook through a settings file, because the CLI subprocess runs it.
`[sdk]`

### B.6 The partial-stream leak

This is the finding that changes a design.

A `MessageDisplay` hook rewrites the **completed-message** surfaces that a
driver reads. It does **not** rewrite the partial stream:

| `stream-json` surface | Content when a hook rewrote the message |
|---|---|
| `assistant.message.content[0].text` | the rewrite |
| `result.result` | the rewrite |
| `text` output format on stdout | the rewrite |
| `stream_event` text deltas | **the original** |
| The transcript `.jsonl` | **the original** |

`[test]`

So a driver that draws `stream_event` deltas for a live typing effect shows the
**original text streaming in**, and then replaces it with the rewrite. The
prior system's `replace` mode is the workaround, and it is documented nowhere:
return `displayContent: ""` for every non-final flush to suppress the streamed
original, then emit the whole rewrite on `final: true`.

### B.7 Tailing the transcript from outside

**1. Name and trigger.** Watch `~/.claude/projects/<project-slug>/<session-id>.jsonl`.
The project slug is the working directory with non-alphanumeric characters
replaced by `-`, truncated at 200 characters plus a path hash if longer.
`[sdk]`

**2. Cadence.** One line appended per conversation event.

**3. Input shape.** Line types observed in a real transcript:
`queue-operation`, `attachment`, `user`, `atis-latch`, `assistant`,
`last-prompt`. An `assistant` line carries the keys `cwd`, `effort`,
`entrypoint`, `gitBranch`, `isSidechain`, `message`, `parentUuid`, `requestId`,
`sessionId`, `timestamp`, `type`, `userType`, `uuid`, `version`. `[test]`

**4. Authority.** None. It is a file the harness owns.

**5. Delivery guarantee.** Not applicable — it is an input, not an output. Two
facts kill it as a live feed: the docs state the transcript **is written
asynchronously and may lag the in-memory conversation**, so it may not yet hold
the current turn when a hook fires; `[docs]` and it never contains a
`MessageDisplay` rewrite. `[test]`

**6. Acknowledgement.** Not applicable.

**7. Budget.** None. It does not block.

**8. Persistence.** Complete and permanent, which is exactly why it holds the
original.

### B.8 What each side can do that the other cannot

**Only an SDK driver can:**

- Use the control protocol (B.3).
- See token-by-token deltas. No hook ever receives a partial line;
  `MessageDisplay` receives whole completed lines.
- Own rendering outright, and so rewrite anything with no timeout, no race,
  and no `verbose` escape hatch.
- Buffer across turns and re-render after the fact.
- Inject follow-up turns with `streamInput()`.
- Read `modelUsage`, `total_cost_usd`, `permission_denials`, `terminal_reason`.
- Supply in-process MCP tools with `createSdkMcpServer()`.

**Only a hook can:**

- **Rewrite assistant text inside a human's interactive session.** This is the
  one capability an SDK driver has no route to.
- Fire inside subagents at every nesting depth.
- Gate or modify **every** tool call, not only the prompted ones.
- Replace tool output as the model sees it.
- Apply to every session on the machine from one settings file, with no driver
  process to launch.
- Ship as a plugin and travel with a repository.
- Emit `terminalSequence` notifications, which the SDK ignores.

---

## Family C — Output styles

**1. Name and trigger.** An output style is a Markdown file with YAML
frontmatter. No event fires it. The harness reads it once, at session start.
`[docs]`

Frontmatter fields:

| Field | Purpose | Default |
|---|---|---|
| `name` | The style name, if not the file name | The file name |
| `description` | Shown in the `/config` picker | none |
| `keep-coding-instructions` | Keep the built-in software-engineering instructions | `false` |
| `force-for-plugin` | Plugin styles only. Applies the style automatically whenever the plugin is enabled, and **overrides the user's `outputStyle` setting**. If several enabled plugins set it, the first loaded wins | `false` |

`[docs]`

Storage:

| Scope | Path |
|---|---|
| User | `~/.claude/output-styles/` |
| Project | `.claude/output-styles/` |
| Managed policy | `.claude/output-styles/` inside the managed settings directory |
| Plugin | an `output-styles/` directory in the plugin |

`[docs]` Project styles load from every `.claude/output-styles/` between the
working directory and the repository root. On a name clash the directory nearest
the working directory wins. `[docs]`

Built-in styles in 2.1.246: Default, Proactive, Concise, Explanatory, Learning.
`[docs]` `[bin]`

Selection: `/config` -> Output style, which writes to
`.claude/settings.local.json`; or the `outputStyle` settings key. **There is no
CLI flag.** The standalone `/output-style` command was deprecated in v2.1.73 and
removed in v2.1.91. `[docs]` `[cli]`

**2. Cadence.** Zero per assistant message. The style text is read once per
conversation. A per-turn reminder is injected as a meta message — the binary's
own string is:

```
`${style} output style is active. ${turnReminder ?? "Remember to follow the specific guidelines for this style."}`
```

`[bin]` That is nagging, not enforcement.

**3. Input shape.** None. An output style receives nothing.

**4. Authority.** It appends its instructions to the **end of the system
prompt**, and by default it **removes** the built-in software-engineering block
(how to scope changes, write comments, verify work). `keep-coding-instructions:
true` keeps that block. `[docs]`

**5. Delivery guarantee.** **The weakest guarantee of every seam in this
document.** An output style is a request to the model, not a transform. There is
no post-processing, no validation, and no retry. Discard modes:

- The model simply does not comply. This is the common case and nothing reports
  it.
- The style named in settings cannot be loaded in the session. The binary's
  string: `"the output style your settings select is not available in this
  session, so it does not apply"`. `[bin]`
- A plugin with `force-for-plugin: true` overrides the user's choice. `[docs]`
- `--safe-mode` does not load output styles. `[cli]`
- **Subagents never apply it.** A subagent runs its own system prompt. A fork is
  the exception, because it inherits the parent's full prompt. `[docs]`
- **A change made mid-session does not apply.** The style is built into the
  system prompt once per conversation. The new style loads on the next `/clear`
  or restart. `[docs]`

**Documentation gap:** no page states whether an output style is still appended
when `--system-prompt` replaces the whole system prompt.

**6. Acknowledgement.** No. There is no feedback channel. The status line's
`output_style.name` field says which style is *loaded*, never whether the model
complied.

**7. Budget.** None, and it does not block. It costs input tokens once, then
rides the prompt cache.

**8. Persistence.** The instruction text is never shown to the user. The model
output it shapes is ordinary transcript text, so it is copyable like any
message.

**Can a sidecar change the active style mid-session?** No. The only route is to
write `outputStyle` to a settings file and then wait for a `/clear` or a new
session. `[docs]`

---

## Family D — The status line

**1. Name and trigger.** The `statusLine` settings key, with `type: "command"`.
The harness runs the command, pipes JSON to its stdin, and paints its stdout at
the bottom of the interface.

Schema, confirmed in the binary:

```
statusLine: {
  type: "command",
  command: string,
  padding?: number,
  refreshInterval?: number,   // seconds, minimum 1
  hideVimModeIndicator?: boolean
}
```

`[bin]` `[docs]` `padding` defaults to 0 and is *additional* to built-in
spacing. `refreshInterval` re-runs the command on a timer, on top of the
event-driven updates. `[docs]`

**2. Cadence.** Once per assistant message, plus other triggers. The documented
list:

- session start, resume included;
- a new assistant message arrives;
- `/compact` finishes;
- the permission mode changes;
- vim mode toggles;
- the `command` value changes;
- a `refreshInterval` timer elapses.

`[docs]` The binary's own trigger set corroborates this: it re-runs when any of
`tokenUsage`, `permissionMode`, `vimMode`, `mainLoopModel`, `fastMode`,
`effortValue`, `thinkingEnabled` or `prStatus` changes, or when
`lastAssistantMessageId` changes. `[bin]`

Throttle: updates are debounced at **300 ms**. `[docs]` The binary constant is
`300`. `[bin]` A change to `command` itself skips the debounce. If a new trigger
arrives while the script is still running, the in-flight script is **cancelled**.
`[docs]`

Known idle gap: event triggers go quiet while the main session waits on
background subagents. `refreshInterval` is the fix. `[docs]`

**3. Input shape.** A live capture from 2.1.246, paths neutralised:

```json
{
  "session_id": "3a39691c-10c9-4d5d-a772-7d4e9707a565",
  "transcript_path": "~/.claude/projects/<project-slug>/3a39691c-….jsonl",
  "cwd": "<working directory>",
  "model": { "id": "claude-haiku-4-5-20251001", "display_name": "Haiku 4.5" },
  "workspace": {
    "current_dir": "<working directory>",
    "project_dir": "<project root>",
    "added_dirs": [],
    "git_worktree": "<worktree name>",
    "repo": { "host": "github.com", "owner": "<owner>", "name": "<repo>" }
  },
  "version": "2.1.246",
  "output_style": { "name": "default" },
  "cost": {
    "total_cost_usd": 0, "total_duration_ms": 1248, "total_api_duration_ms": 0,
    "total_lines_added": 0, "total_lines_removed": 0
  },
  "context_window": {
    "total_input_tokens": 0, "total_output_tokens": 0,
    "context_window_size": 200000,
    "current_usage": null, "used_percentage": null, "remaining_percentage": null
  },
  "exceeds_200k_tokens": false,
  "fast_mode": false,
  "thinking": { "enabled": true },
  "vim": { "mode": "INSERT" }
}
```

`[test]`

The documented full schema adds these optional blocks: `session_name`,
`prompt_id`, `effort.level`, `rate_limits.five_hour` and
`rate_limits.seven_day` (each with `used_percentage` and `resets_at`),
`agent.name`, `pr` (with `number`, `url`, `review_state`, `kind`), and
`worktree` (with `name`, `path`, `branch`, `original_cwd`, `original_branch`).
`[docs]` The binary's construction of the payload matches field for field.
`[bin]`

Fields that can be `null`: `context_window.current_usage`,
`context_window.used_percentage`, `context_window.remaining_percentage` —
before the first API call, and again after `/compact`. `[docs]`

**4. Authority.** Only the status line rows. It cannot touch message text, the
transcript, or the model.

What it may render:

- **Multiple lines.** Each `echo` becomes a row. No documented cap; a probe
  rendered 12 rows successfully. `[docs]` `[test]`
- **ANSI colour.** Supported. Plain text is painted dim grey.
- **Emoji.** Yes.
- **OSC 8 hyperlinks**, terminal permitting. `FORCE_HYPERLINK=1` overrides
  detection.
- **Width.** No documented character limit. The docs say only that long output
  "may get truncated or wrap awkwardly". Read the `COLUMNS` and `LINES`
  environment variables, which the harness sets from v2.1.153. In a
  pseudo-terminal with no reported size they are **unset**, so always default
  them. `[docs]` `[test]`
- Documented fragility: "Multi-line status lines with escape codes are more
  prone to rendering issues than single-line plain text." `[docs]`

**5. Delivery guarantee.** No. Discard modes:

- **Print mode and any non-interactive run.** Nothing is drawn, because there is
  no interface. Measured: a probe script that writes a file on every invocation
  produced no file under `-p`, and produced one immediately under an interactive
  pseudo-terminal. **The documentation never states this.** `[test]`
- Workspace trust not accepted. The binary logs `Status line command skipped:
  workspace trust not accepted`. `[bin]`
- `disableAllHooks` in managed settings turns it off entirely. The binary warns
  `Status line is configured but disableAllHooks is true`. `[bin]`
- `allowManagedHooksOnly`, or `disableAllHooks` outside managed settings, or
  `--safe-mode`: the user's value is skipped **without warning**. `[docs]`
- The script exits non-zero, or prints nothing: the row is blank. `[docs]`
- A newer trigger cancels the in-flight script: the old text stays. `[docs]`
- The row is hidden during autocomplete suggestions, the help menu, and
  permission prompts. `[docs]`
- Outside fullscreen rendering, notifications share the row and can truncate it.
- On Windows with Git Bash, backslashes in the command path are eaten and it
  fails with no visible error. `[docs]`

**6. Acknowledgement.** No. The script can log that it ran. Nothing reports that
its text was painted.

**7. Budget. Documentation gap** — no timeout value is stated, and it could not
be resolved from the binary. The documented behaviour instead: "Slow scripts
block the status line from updating until they complete", and a newer trigger
cancels an in-flight run. **It does not block the agent.** It runs locally and
costs no tokens. A slow script makes only its own row stale. `[docs]`

**8. Persistence.** **No.** The row is repainted in place; the captured
interface stream shows cursor-positioning escapes overwriting the same rows.
Status-line output never enters the transcript, so `ctrl+o` cannot show it. A
sidecar cannot recover a value it wrote two seconds ago; it must keep its own
log. The docs do not say this in one sentence, so it is a
**documentation gap** with conclusive indirect evidence. `[test]`

---

## Family E — Slash commands and skills

### E.0 They are now one thing

Custom slash commands have been **merged into skills**. A file at
`.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md`
both create `/deploy` and behave the same way. Existing `.claude/commands/`
files keep working. `[docs]` There is no longer a separate slash-command
documentation page.

Also renamed: the model-facing tool is **`Skill`**, not `SlashCommand`.
Permission syntax is `Skill(commit)` for an exact match and `Skill(review-pr *)`
for a prefix match. `PreToolUse` matches on `Skill`. `[docs]`

### E.1 The decisive fact

**Invoking a command or a skill injects a prompt. It does not print anything.**
Three independent statements say so:

- "When you or Claude invoke a skill, the rendered `SKILL.md` content enters the
  conversation as a single message and stays there for the rest of the
  session." `[docs]`
- "Skills and commands inject their instructions as user messages at the point
  of invocation." `[docs]`
- Bundled skills are described as "a prompt handed to Claude", in contrast with
  built-in commands "whose behavior is coded into the CLI". `[docs]`

So a user-authored command always causes a model turn. Only **built-in**
commands (`/status`, `/help`, `/config`, `/tasks`) run fixed CLI logic and
render directly, and a user cannot add to that set. `[docs]`

### E.2 Can a command print without a model turn?

Not from inside the command file. The three mechanisms that look as if they
might, and why they do not:

| Mechanism | Where the text goes |
|---|---|
| `` !`command` `` dynamic injection | Into the prompt text sent to the model. **Whether the terminal shows anything during injection is a documentation gap** |
| `@file` reference | Attaches file contents for the model |
| A bundled script | Only if the model calls it with the Bash tool, which is a model turn |

Three mechanisms **outside** the command file do print without a model turn:

1. **`UserPromptExpansion` hook with `decision: "block"` and a `reason`.** The
   hook fires when a typed command expands into a prompt, before it reaches the
   model. Blocking stops the expansion, so there is no model turn, and `reason`
   is shown to the user. This is the cleanest zero-token "print text in answer
   to a typed command" path in the product. `[docs]`
2. **`systemMessage` from any hook**, subject to every discard rule in A.3.
3. **The user's own `!` shell mode** in the input box. Since v2.1.186 the model
   responds to it automatically unless `respondToBashCommands: false`. `[docs]`

### E.3 The eight questions

**1. Name and trigger.** A typed `/name`, or the `Skill` tool. The hook events on
those paths are `UserPromptExpansion` (typed) and `PreToolUse` / `PostToolUse`
with matcher `Skill` (model-called). Typing directly **bypasses `PreToolUse`**;
only `UserPromptExpansion` covers that path. `[docs]`

**2. Cadence.** Zero per assistant message. It fires once per invocation, and it
*precedes* the assistant message rather than reacting to one.

**3. Input shape.** The command itself receives no structured payload — only
argument substitution and `${CLAUDE_*}` variables. The hook around it does:

```json
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/<project-slug>/00893aaf.jsonl",
  "cwd": "<working directory>",
  "permission_mode": "default",
  "hook_event_name": "UserPromptExpansion",
  "expansion_type": "slash_command",
  "command_name": "example-skill",
  "command_args": "arg1 arg2",
  "command_source": "plugin",
  "prompt": "/example-skill arg1 arg2"
}
```

`[docs]`

**4. Authority.** The prompt content that reaches the model, the tool grants for
that turn, and the model and effort for that turn. **Not the rendered output.**

Frontmatter that carries that authority: `description`, `argument-hint`,
`allowed-tools` (cleared at the next user message), `disallowed-tools`, `model`
(for the rest of the turn, not saved), `disable-model-invocation`,
`user-invocable`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`,
`shell`. `[docs]`

Argument placeholders: `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N`, and `$name` for
named arguments. **`$N` is 0-based** — `$0` is the first argument. `[docs]`

**5. Delivery guarantee.** Not applicable in the direct sense, because it never
renders. What it produces is a model turn, so it inherits every reliability
problem of Family C. Additional discard modes:

- `--disable-slash-commands` (the 2.1.246 help text is "Disable all skills").
  `[cli]`
- `disableBundledSkills`, `skillOverrides: "off"`.
- A name clash where another source wins. Precedence is enterprise > personal >
  project; a skill beats a command file of the same name.
- `disableSkillShellExecution` replaces every `!` command with
  `[shell command execution disabled by policy]`.
- **A failed injected command aborts the whole invocation**, not just its own
  placeholder, so the model never sees the content. So does an injected command
  whose permission check is anything but allow. `[docs]`
- A `UserPromptExpansion` hook blocks it.
- `--safe-mode` loads no skills. `--bare` skips auto-discovery, though skills
  still resolve by `/skill-name`. `[cli]`
- A nested skill directory below the start point is invisible until the model
  reads or edits a file inside it. `[docs]`
- Cloud sessions do not read `~/.claude/skills/`.

**6. Acknowledgement.** No. A `UserPromptExpansion` or `PostToolUse` hook can
confirm **invocation**. Invocation is not display.

**7. Budget.** Injected `!` commands run under the Bash tool's two-minute
default timeout and block the invocation. A foreground fork blocks the turn; a
background fork does not. `UserPromptExpansion` hooks default to 600 s.

**8. Persistence.** Yes, for the injected content — it is a real conversation
message, so it is in the transcript. Auto-compaction re-attaches the most recent
invocation of each skill after the summary, keeping the first 5 000 tokens each
inside a shared 25 000-token budget. `[docs]`

### E.4 Skill-specific notes

**What a skill can put on screen: nothing directly.** Skill content is injected
into the model's context; it is never rendered to the user as skill content.
**Documentation gap:** no page describes what the interface draws when a skill
is invoked.

**Can a skill's script stdout reach the terminal?** Two paths, one screen:

| Path | Reaches the screen? |
|---|---|
| `` !`command` `` injection | **No.** The output is substituted into the text sent to the model |
| A Bash tool call the model makes | **Yes**, as a tool result in the transcript. Truncated under `viewMode: "default"`, full under `"verbose"`, a one-line summary under `"focus"` |

`[docs]`

**Subagent versus main loop.** By default a skill runs inline in the main loop.
`context: fork` runs it in a subagent, and then:

- The skill content becomes the subagent's prompt. It has no access to the
  conversation history.
- It runs in the **background by default** from v2.1.218. `background: false`
  waits inside the invoking turn.
- The harness waits regardless of `background` under `-p` or the SDK, with
  `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, on a second invocation while the
  first still runs, and for a scheduled task.
- A backgrounded fork's edits are **outside the checkpoints**, so `/rewind` does
  not undo them.
- **Output styles do not apply to it.**

`[docs]`

**Discovery.** `.claude/skills/` in the launch directory and every parent up to
the repository root, plus `.claude/skills/` and `.claude/commands/` in each
`--add-dir` directory. Note that `permissions.additionalDirectories` in settings
does **not** do this — only the flag and the slash command do. Only the
`description` and `when_to_use` fields sit in context by default, capped at
1 536 characters combined; the body loads on invocation and stays for the
session. `[docs]`

---

## Family F — Out-of-band paths

These do not go through the harness's rendering layer at all. That is their
strength and their weakness: nothing can discard them, and nothing integrates
them with the conversation.

### F.1 A file on disk

**1. Name and trigger.** A `PostToolUse` hook on `Write|Edit` rewrites the file
the agent just wrote. This is exactly what the prior system's second script did.

**2. Cadence.** Once per matching tool call. Zero or many per assistant message.

**3. Input shape.** The `PostToolUse` payload, with `tool_input.file_path` and
`tool_response`:

```json
{
  "session_id": "abc123",
  "transcript_path": "~/.claude/projects/<project-slug>/00893aaf.jsonl",
  "cwd": "<working directory>",
  "permission_mode": "default",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": { "file_path": "/path/to/file.txt", "content": "file content" },
  "tool_response": { "filePath": "/path/to/file.txt", "success": true },
  "tool_use_id": "toolu_01ABC123…",
  "duration_ms": 12
}
```

`[docs]`

**4. Authority.** The bytes on disk. Complete and unmediated. This is the only
seam in this document that changes durable state rather than a rendering.

**5. Delivery guarantee.** The write itself is guaranteed — it is an ordinary
file write. **Reaching the user's eyes is not**, because the user must open the
file. The hook can still be removed by `disableAllHooks`, `--safe-mode`,
`--bare`, or an untrusted workspace.

**6. Acknowledgement.** The sidecar can read the file back. This is the **only
seam that gives real acknowledgement**, and only of the write, not of the
reading.

**7. Budget.** The hook's own timeout — 600 s by default for a command hook. It
blocks the agent loop while it runs. The prior system used 180 s here.

**8. Persistence.** Permanent. The file is the record. That is also the risk:
the change is not reversible by the harness, and the model sees the rewritten
file on its next read.

### F.2 A desktop notification, a terminal bell, and the terminal title

**1. Name and trigger.** The `terminalSequence` field on any hook's JSON output.
The harness emits the escape sequence on the hook's behalf. `[bin]`

**4. Authority.** Only these sequences pass: OSC 0, 1, 2 (window and tab title),
OSC 9 (iTerm2 notification), OSC 99, OSC 777 (desktop notification), and BEL.
**Anything else is dropped.** `[bin]`

**5. Delivery guarantee.** No. It is **written only in an interactive session,
only while the interface is on screen**, and it is **ignored entirely in print
mode and the SDK**. `[docs]` `[sdk]` The terminal must also support the
sequence. `StopFailure` discards every output field *except* this one; a dozen
other events discard it along with everything else.

**6. Acknowledgement.** No.

**7. Budget.** The hook's own.

**8. Persistence.** No. A notification is transient by definition; a title is
overwritten by the next one.

The harness has its own notification channel too, selected in `/config` — Auto,
iTerm2 (OSC 9), or Terminal Bell. `[bin]` That is a harness feature, not a
sidecar seam.

### F.3 A second terminal, a tmux pane, or a separate window

**1. Name and trigger.** The sidecar writes to another terminal device, or runs
its own interface. Nothing in the harness is involved.

**2. Cadence.** Whatever the sidecar chooses.

**3. Input shape.** Whatever the sidecar reads. In practice: the transcript file
(B.7), or a hook payload it forwards to itself.

**4. Authority.** Total, inside its own window.

**5. Delivery guarantee.** **Absolute for the window it owns.** No harness
setting can discard it. This is the only seam with a genuinely unconditional
guarantee. The catch is that it is not the window the user is reading, and the
sidecar cannot know whether the user looked.

**6. Acknowledgement.** Of the write, yes. Of the reading, no.

**7. Budget.** None, and it does not block the agent.

**8. Persistence.** Whatever the sidecar keeps.

The harness offers a related facility rather than an attachment point: the
`--worktree` and `--tmux` flags create a git worktree and a tmux session for it,
with iTerm2 native panes when available. `[cli]`

### F.4 A web page

Artifacts. The agent publishes an HTML page and hands the user a URL. This is a
model-invoked tool, not a sidecar seam, but it is a real path from the session
to something the user reads. The page is published reliably; the user must open
the link. It persists and can be shared.

### F.5 Remote control and cross-session messaging

The harness carries several session-to-elsewhere paths. None is an interception
point. They are listed so a design does not mistake them for one.

| Path | What it is | A rewrite seam? |
|---|---|---|
| Remote Control (`--remote-control`, `/remote-control`) | Registers with the Anthropic API and mirrors the terminal for a **person** on claude.ai or the mobile app. Starts only when a human runs it | **No.** It routes through Anthropic servers and injects *input*. It does not intercept output |
| `messaging_socket_path`, advertised in the `system/init` message | A local socket for cross-session messaging | Sends *messages into* a session, not text onto its screen. Undocumented |
| `--brief` and the `SendUserMessage` tool | Agent-to-user communication, invoked by the **model** | **No.** The model decides when to call it. A sidecar cannot |
| `claude agents` and `--bg` | Background agent sessions | A separate session with its own output, not an attachment to this one |

`[cli]` `[sdk]` `[test]`

### F.6 The transcript export commands

`/export` writes the conversation out, and `[` in transcript view writes the
full conversation to native terminal scrollback. `[docs]` Both carry the
**original** assistant text, never a `MessageDisplay` rewrite. `[test]` They
matter because they are the route by which a user discovers that the rewrite was
cosmetic.

---

## Family G — Plugins and marketplaces

### G.1 What a plugin may register

A plugin is a directory with a `.claude-plugin/plugin.json` manifest. The
scaffold that `claude plugin init` writes contains: `plugin.json`, a command
Markdown file, `hooks/hooks.json`, a `hooks-handlers/` directory, `.lsp.json`,
an `output-styles/` directory, an MCP `server.ts`, and a skill. `[bin]`

The binary's own conflict message names the manifest-declarable component
types exactly:

> `has both plugin.json and marketplace manifest entries for
> commands/agents/skills/hooks/outputStyles/themes/syntaxHighlighting. This is a
> conflict.`

`[bin]`

So the full component list is:

| Component | Can it put text on the screen? | Route |
|---|---|---|
| **Hooks** (`hooks/hooks.json`) | **Yes — including `MessageDisplay`** | Family A. This is the only plugin component that rewrites assistant prose |
| Slash commands / skills | No, not directly | They inject a prompt (Family E) |
| Agents (subagents) | Only through a model turn | — |
| **Output styles** | Only by asking the model | Family C. A plugin style with `force-for-plugin: true` **overrides the user's own `outputStyle` setting** |
| Themes and syntax highlighting | Colour only, not text | — |
| **MCP servers** (`.mcp.json`) | Only through tool results the model asked for | Family H |
| LSP servers (`.lsp.json`) | No | — |
| Settings and sandbox configuration | No | — |

**A plugin cannot ship a `statusLine`.** The status line is a settings key, not
a plugin component type, and it is not in the manifest list. **Documentation
gap** on whether a plugin's bundled settings file can carry one.

**There is no plugin extension point that post-processes assistant message text
other than the `MessageDisplay` hook.** A plugin registers no daemon and no
background process of its own; every hook fire is a fresh subprocess unless the
hook is of type `http`.

### G.2 The manifest and the marketplace

The prior system's manifest and marketplace, quoted from this repository's own
prior-art notes, are the working shape:

```json
{
  "name": "<plugin>",
  "description": "…",
  "version": "0.1.1-…",
  "author": { "name": "…" },
  "homepage": "…",
  "repository": "…",
  "license": "MIT",
  "keywords": ["hooks", "claude-code"]
}
```

Note there is **no `hooks` key**. The harness discovers `hooks/hooks.json` by
its conventional location inside the plugin.

A repository can be its own marketplace with
`.claude-plugin/marketplace.json` and `"source": "./"`, which points the entry
at the repository root.

`claude plugin` subcommands in 2.1.246: `details`, `disable`, `enable`, `eval`,
`init`/`new`, `install`/`i`, `list`, `marketplace`, `prune`/`autoremove`,
`tag`, `uninstall`/`remove`, `update`, `validate`. `[cli]`

Session-only loading: `--plugin-dir <path>` (a directory or a `.zip`,
repeatable) and `--plugin-url <url>`. `[cli]` These are the cheapest way to test
a sidecar plugin without installing it.

### G.3 The eight questions

**1. Name and trigger.** A plugin fires nothing on its own. It is a container
for the components in G.1, each of which is answered in its own family.

**2. Cadence.** Whatever the registered component's cadence is.

**3. Input shape.** Whatever the registered component receives.

**4. Authority.** The union of its components' authority. For display purposes
that means: the `MessageDisplay` hook, and nothing else.

**5. Delivery guarantee.** Everything in A.3, plus these plugin-specific
discards:

- `strictPluginOnlyCustomization` and `disableCommandPluginSources` in managed
  settings. `[bin]`
- `--safe-mode` disables plugins. `--bare` skips plugin sync. `[cli]`
- **Plugin shadowing.** The binary warns when a directory-loaded plugin
  `shadowed the project's` copy of the same name, and when a workspace was not
  trusted at scan time: `skipped because this workspace was not trusted when
  plugins were scanned. After accepting the trust dialog, run /reload-plugins
  (or relaunch) to load what qualifies.` `[bin]`
- A plugin delisted from its marketplace is auto-uninstalled. `[bin]`
- Plugin `hooks/`, `.mcp.json`, `agents/` and `output-styles/` changes need
  `/reload-plugins`. `[docs]`

**6. Acknowledgement.** No, beyond what each component offers.

**7. Budget.** Each component's own.

**8. Persistence.** Each component's own.

---

## Family H — MCP servers

### H.1 What the client actually listens for

An MCP server is a tool provider. The design question is whether it can push
text to the display **unprompted** — without the model calling one of its tools.

The 2.1.246 client registers notification handlers for exactly these methods:

```
notifications/cancelled
notifications/progress
notifications/elicitation/complete
notifications/prompts/list_changed
notifications/resources/list_changed
notifications/tasks/status
notifications/tools/list_changed
```

`[bin]`

**There is no handler for `notifications/message`.** The MCP logging channel is
in the bundled protocol library, and the server side can send it, but the
Claude Code client registers nothing to receive it. So **an MCP server's log
messages do not reach the user's screen.** `[bin]`

`notifications/progress` is handled by the base protocol class and resolves the
progress callback of an **in-flight request**. It is therefore only usable while
a tool call the model made is running.

### H.2 The routes that do reach the screen

| Route | Reaches the screen? | Unprompted? |
|---|---|---|
| A tool result | Yes, rendered in the transcript | **No.** The model must call the tool |
| A resource, `@server:protocol://resource` | Yes, when the user references it | No. The user must type it |
| A prompt, `/mcp__server__prompt` | It injects a prompt, like any skill (Family E) | No. The user must type it |
| `elicitation/create` | **Yes — a dialog** | **Yes, in principle.** The client supports elicitation and queues it in application state, and the `Elicitation` hook event exists for it. It asks for input; it is not a text display |
| `sampling/createMessage` | Runs a model call for the server | Not a display route |
| `notifications/message` (logging) | **No handler in 2.1.246** | — |
| `notifications/progress` | Only inside an in-flight request | No |

`[bin]`

### H.3 The eight questions

**1. Name and trigger.** An MCP server configured in `.mcp.json`, in settings,
or by `--mcp-config`. Transports: stdio, SSE, HTTP. `[cli]` Its tools appear to
the model as `mcp__<server>__<tool>`, or
`mcp__plugin_<plugin>_<server>__<tool>` for a plugin-bundled server. `[docs]`

**2. Cadence.** Zero per assistant message. It fires when the model calls a
tool.

**3. Input shape.** The MCP protocol's `tools/call` request. The tool result
comes back as `{ content: [...], structuredContent?: {...}, isError?: bool }`.
`[bin]`

**4. Authority.** Its own tool results, its resources, and its prompts. It has
no authority over assistant prose.

**5. Delivery guarantee.** A tool result is rendered, subject to truncation by
`viewMode` and to the `MAX_MCP_OUTPUT_TOKENS` cap. `[bin]` Unprompted text has
no route at all, except an elicitation dialog. An unapproved `.mcp.json` server
is shown as pending approval and is **not connected to**. `[cli]`
`--strict-mcp-config` ignores every configuration except `--mcp-config`.
`[cli]`

**6. Acknowledgement.** No.

**7. Budget.** `MCP_TIMEOUT` for server startup and `MCP_TOOL_TIMEOUT` for a
tool call. `[bin]` A tool call blocks the agent loop.

**8. Persistence.** Tool results are conversation content, so they are in the
transcript and survive.

### H.4 Verdict for a rewriting sidecar

**An MCP server is the wrong seam.** It cannot see assistant prose and it cannot
write unprompted. Its one relevance is indirect: a `MessageDisplay` hook may be
of `type: "mcp_tool"`, so an MCP server can be the *implementation* of the
rewriter that the hook calls. `[docs]` That is a transport choice inside
Family A, not a separate attachment point.

---

## What the documentation does not answer

A named gap is worth more than a guess. These are the questions this
investigation could not settle from a primary source.

1. **Status line timeout.** No value in the status-line page, the settings
   reference, or the binary. Only the behaviour is documented: a slow script
   blocks its own row, and a newer trigger cancels an in-flight run.
2. **Status line behaviour in print mode.** Never stated. A probe shows it does
   not run. That finding is empirical, not documented.
3. **Status line maximum line count and maximum width.** Only "may get truncated
   or wrap awkwardly". A probe rendered 12 rows successfully.
4. **Whether status line output can be recovered after a repaint.** Never
   stated. Every indirect signal says no.
5. **Whether `statusLine` runs under `--bare`.** `--bare` says "skip hooks". The
   status line is gated with hooks in `disableAllHooks` but is not named in the
   `--bare` list.
6. **Interaction between `--system-prompt` and `outputStyle`.** No page states
   whether a style is still appended when the whole system prompt is replaced.
7. **Whether `` !`command` `` injection output appears in the terminal** during
   skill expansion, or only in the injected prompt text.
8. **What the interface draws when a skill is invoked** — the row, the label,
   the content preview. Never described.
9. **Precedence between two `MessageDisplay` hooks** that both return
   `displayContent`. The docs say only that matching hooks run in parallel. A
   test observed the winner change between identical runs.
10. **`MessageDisplay` batch boundaries.** "Batch boundaries depend on how the
    text streams", with no rule given. The binary shows the rule is the last
    newline, subject to a 100 ms rate limit and a cap of 3 in-flight processes,
    but this is code, not contract.
11. **Whether `MessageDisplay` fires for subagent text** under
    `--forward-subagent-text`.
12. **`MessageDisplay` on non-terminal surfaces** — the desktop app, IDE
    extensions, and the web. The docs say all surfaces fire the same hook
    events, but do not describe the rendering.
13. **How `displayContent` reaches an SDK or print-mode driver.** The docs call
    the event "display-only" and never state that it replaces
    `assistant.message.content[].text` and `result.result`. Established here by
    measurement.
14. **Whether a plugin's bundled settings can carry a `statusLine`.**
15. **Maximum hook timeout.** No global maximum is documented for any hook type.
    Only `SessionEnd` has a stated 60-second cap.
16. **Whether `systemMessage` is persisted in the transcript.** Documented for
    `additionalContext`, never for `systemMessage`.
17. **`--include-partial-messages` and `MessageDisplay`.** A test shows partial
    deltas carry the original; the docs do not say so.

---

## The comparison table

Read down the left column, across the top. Question 5 is the one that decides.

| Attachment point | 1. Trigger | 2. Fires per assistant message | 3. Receives | 4. May change | 5. Guaranteed to reach the screen? What discards it | 6. Can confirm display? | 7. Budget / blocks? | 8. Re-readable later? |
|---|---|---|---|---|---|---|---|---|
| **`MessageDisplay` hook** | Assistant text is being displayed | Interactive: 1+ per message, one flush per completed-line batch, `final:true` on the last. Print/SDK: exactly 1 per message with text. 0 for tool-only messages | `session_id`, `transcript_path`, `cwd`, `prompt_id`, `hook_event_name`, `turn_id`, `message_id`, `index`, `final`, `delta`. No `permission_mode`, no `effort` | `displayContent` — the rendered text of that flush. Nothing else | **No.** Discarded by: **`verbose`** (interactive, silent); hook error or timeout (falls back to the original, logged only to the debug log); a second `MessageDisplay` hook winning a non-deterministic race; `disableAllHooks`; `allowManagedHooksOnly`; untrusted workspace; `--safe-mode`; `--bare`; an invalid settings file under `-p` (silently ignored). Only the **first** text block of a message shows it | **No.** No acknowledgement channel. In print/SDK only, `--include-hook-events` echoes the hook's own stdout back, and the rewrite is visible in the `assistant` and `result` messages | **10 s** default — not 600 s. Per-hook `timeout` raises it. **It blocks rendering**; the harness holds each flush | **No.** Never in the transcript. `ctrl+o`, `--resume`, `/export` and `verbose` all show the original. It survives only in terminal scrollback |
| **`Stop` hook** | Just before the turn ends | 1 per turn, not per message. Does not fire on interrupt or API error | `last_assistant_message`, `stop_hook_active`, `background_tasks`, `session_crons`, plus the common fields | `systemMessage`, `stopReason`, `terminalSequence`. `additionalContext` and blocking `reason` go to the **model** | **No**, and it is too late anyway — the text is already rendered. `systemMessage` is discarded by `--output-format text` and `json`; `terminalSequence` by print mode and the SDK. Blocking makes the model write **more** | No | Command hook default 600 s. **Blocks** | Blocking feedback appears in the transcript as `Stop hook feedback` |
| **`PostToolUse` hook** | After a tool call | 0 or many | `tool_name`, `tool_input`, `tool_response`, `tool_use_id`, `duration_ms` | `updatedToolOutput` — the tool result **as the model sees it**; `additionalContext` to the model. **Never assistant prose** | Not applicable to prose. Exit-0 stdout shows only in transcript mode | No | 600 s default. **Blocks** | The replaced tool output is conversation content and persists |
| **`PostToolUse` on `Write`/`Edit`, rewriting the file** | After a file write | 0 or many | As above | **The bytes on disk** | **The write is guaranteed.** Reaching the user's eyes is not — the user must open the file. Removed by `disableAllHooks`, `--safe-mode`, `--bare`, untrusted workspace | **Yes**, by reading the file back. The only seam with real acknowledgement | 600 s default, 180 s in the prior system. **Blocks** | **Permanent.** The file is the record, and the model reads the rewrite next time |
| **`UserPromptExpansion` hook, blocking** | A typed `/command` expands | 0. It precedes the message | `expansion_type`, `command_name`, `command_args`, `command_source`, `prompt` | The `reason` shown to the user when it blocks | Reaches the screen in interactive mode. Costs no tokens and needs no model turn. Subject to every hook discard in A.3 | No | 600 s default. **Blocks** | The block notice is in the transcript |
| **`PostCompact` hook** | After compaction | 0. Once per compaction | `trigger`, `compact_summary` | Exit-0 stdout, which is **shown to the user** | One of the few events whose stdout is documented as shown to the user. Discards `systemMessage` and `continue` | No | 600 s default. **Blocks** | Documentation gap |
| **`terminalSequence` on any hook** | Any hook's JSON output | As the host event | As the host event | Only OSC 0, 1, 2, 9, 99, 777 and BEL. Everything else is dropped | **No.** Interactive only, and only while the interface is on screen. **Ignored entirely in print mode and the SDK** | No | The host hook's | **No.** Transient by nature |
| **Output style** | A file read at session start | 0. Read once per conversation | Nothing | The tail of the system prompt, and it drops the built-in coding block by default | **No — the weakest guarantee here.** It is a request the model may ignore, with no validation and no retry. Also discarded by: the style being unavailable in the session (silent); a plugin `force-for-plugin` override; `--safe-mode`; every subagent; **any change made mid-session, which needs `/clear`** | No. The status line reports which style is *loaded*, never compliance | None. Does not block | The instructions are never shown. The output they shape is normal transcript text |
| **Status line** | The `statusLine` settings key | 1 per assistant message, plus 6 other triggers, debounced 300 ms | A large JSON object: `session_id`, `model`, `workspace`, `version`, `output_style`, `cost`, `context_window`, `rate_limits`, `vim`, `agent`, `pr`, `worktree`, and more | Only the status-line rows. Multi-line, ANSI colour, emoji, OSC 8 links | **No.** Discarded by: **print mode and every non-interactive run**; untrusted workspace; `disableAllHooks`; `allowManagedHooksOnly` (silent); `--safe-mode` (silent); a non-zero exit; empty output; a newer trigger cancelling the in-flight run; autocomplete, help and permission prompts hiding the row; a notification overwriting it | **No** | **Timeout is a documentation gap.** Does not block the agent; blocks only its own row | **No.** Repainted in place, never in the transcript |
| **Slash command or skill** | A typed `/name`, or the `Skill` tool | 0. It precedes the message | Argument substitution and `${CLAUDE_*}` variables only | The prompt sent to the model, the turn's tool grants, model and effort. **Not the rendered output** | **It never renders.** It causes a model turn, so it inherits every reliability problem of an output style. Also discarded by `--disable-slash-commands`, `skillOverrides: "off"`, a name clash, `disableSkillShellExecution`, a failed injected command aborting the whole invocation, `--safe-mode` | No. A hook can confirm invocation, which is not display | Injected `!` commands run under the Bash tool's 2-minute default and block the invocation | **Yes.** The injected content is a conversation message and survives compaction within a 25 000-token re-attach budget |
| **Plugin** | A container, not an event | Whatever its components do | Whatever its components receive | The union of its components. For display that means the `MessageDisplay` hook and nothing else | As its components, plus `strictPluginOnlyCustomization`, `disableCommandPluginSources`, `--safe-mode`, `--bare`, plugin shadowing, an untrusted workspace at scan time, and auto-uninstall on delisting | No | Its components' | Its components' |
| **MCP server** | The model calls one of its tools | 0 | The MCP `tools/call` request | Its own tool results, resources and prompts. **Never assistant prose** | A tool result renders, subject to `viewMode` truncation and `MAX_MCP_OUTPUT_TOKENS`. **Unprompted text has no route: 2.1.246 registers no handler for `notifications/message`.** An unapproved `.mcp.json` server is not connected to | No | `MCP_TIMEOUT`, `MCP_TOOL_TIMEOUT`. A tool call **blocks** | **Yes.** Tool results are conversation content |
| **SDK driver that owns the interface** | `query()` | 1 `assistant` message, plus many `stream_event` partials | The full `SDKMessage` union | Anything, in its own rendering | **Yes, unconditionally — for its own window.** It has **zero reach** into an interactive session it did not start | **Yes** | None. Does not block | Whatever it stores |
| **Print mode, `claude -p`** | One invocation | 1 result | `text`, `json` or `stream-json` on stdout | Anything, in its own rendering | Guaranteed for its own output. Note: **settings files that fail validation are silently ignored under `-p`** | Yes | None | Whatever the caller stores |
| **Tailing the transcript `.jsonl`** | A file watch | 1 line per event | `queue-operation`, `attachment`, `user`, `assistant`, `last-prompt` lines | **Nothing.** Read-only | Not applicable. It is an input. It **lags the in-memory conversation** by design, and never contains a `MessageDisplay` rewrite | Not applicable | None. Does not block | **Yes**, permanently — which is why it holds the original |
| **A second terminal or window** | The sidecar's own process | Whatever it chooses | Whatever it reads | Anything, in its own window | **Yes, absolutely.** No harness setting can discard it. But it is not the window the user is reading | Of the write, yes. Of the reading, no | None. Does not block | Whatever it keeps |
| **Remote Control** | A human runs it | — | — | It injects *input* | **Not an interception point.** It routes through Anthropic servers and mirrors the terminal for a person | — | — | — |

---

## Recommendation

**Attach at `MessageDisplay`.** It is the only seam that rewrites assistant
prose before it is rendered, it works in the interactive interface and in print
mode from one implementation, and its failure mode is fail-open — a dead
sidecar shows the original answer rather than breaking the session.

**Budget for 10 seconds, not 60.** The default on this event is 10 s, and a
sidecar that does not set `timeout` explicitly will be killed silently on any
message that needs a real model call. Set `timeout` in the hook entry, and use
`type: "http"` against a long-lived process so a slow process spawn is not part
of the budget.

**Solve the acknowledgement gap first, because the prior design did not.** The
sidecar cannot learn that `verbose` was on, that a second `MessageDisplay` hook
won the race, or that its output was dropped. Before any rewriting logic is
written, build the check that answers "was my output rendered, and if not,
why not?" — the `verbose` setting is readable from the same settings files the
hook is registered in, and the debug log records every fire.
