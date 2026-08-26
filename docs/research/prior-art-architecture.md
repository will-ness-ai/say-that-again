# Design digest — the prior system

A sidecar that rewrites a coding agent's on-screen messages into plainer language
with a local LLM. This digest is written so an engineer who has never seen the
source can redraw the architecture from it alone.

## Naming note

Two families of identifier in the original name the project itself. They are
replaced here by neutral stand-ins, consistently, everywhere in this document
including the quoted code:

| Stand-in used here | What it replaces |
|---|---|
| `REWRITE_` (env var prefix) | the project-derived prefix on every environment variable |
| `<plugin>` | the plugin/package name, where it appears in paths, markers, and on-screen strings |

Every other identifier is verbatim from the source. File paths are given as
repository-relative paths.

---

## 1. Purpose and scope

**What it does.** After the harness has produced an assistant message, the prior
system sends that message to a local LLM, asks for a plain-English rewrite, and
puts the rewrite on screen. A second, opt-in hook does the same thing to Markdown
*files* the agent writes.

**Two rewriters, deliberately separate:**

| | Display rewrite | Markdown-file rewrite |
|---|---|---|
| Script | `rewrite.sh` | `rewrite-md.sh` |
| Trigger | every streamed chunk of an assistant message | after a `Write` or `Edit` tool call |
| Changes bytes on disk? | **No** | **Yes** |
| Default state | on | **off** (needs a directory opt-in) |

**What it leaves alone — the load-bearing scope boundary.** The display rewriter
is *display-only*. It changes the string the terminal renders and nothing else:

- the agent's own context and reasoning still see the original text;
- the saved transcript still holds the original text;
- no message is ever suppressed or replaced in storage.

This is enforced structurally, not by convention: the display hook's only output
channel is a `displayContent` field the harness renders, and it never writes to
the transcript.

**What it explicitly does not touch:**

- messages whose prose (fenced code stripped) is under a character floor —
  short acknowledgements are not worth an LLM round trip;
- fenced code blocks — the system prompt instructs the model to reproduce them
  unchanged (an instruction, not a parser guarantee);
- YAML frontmatter in the file rewriter — split off mechanically before the LLM
  sees the text and re-attached verbatim after;
- any Markdown file outside the single opted-in directory;
- any file the file rewriter already rewrote (idempotency marker).

**Failure posture: fail open, always.** Every error path — feature disabled,
missing `jq`, missing `curl`, unparseable payload, LLM unreachable, LLM timeout,
empty completion, failed temp write — exits 0 and emits nothing, which leaves the
original text on screen and the original file on disk. The design premise is that
a display filter must never be able to swallow or corrupt an answer.

---

## 2. Repository layout — complete file census

Eight files. There are no others, in any branch or anywhere in history.

```
.claude-plugin/
├── plugin.json         # plugin manifest (name, version, author, license, keywords)
└── marketplace.json    # lets the repo serve as its own single-plugin marketplace
hooks/
└── hooks.json          # THE integration point: event -> script registration
rewrite.sh              # display-rewrite hook          (361 lines, bash)
rewrite-md.sh           # Markdown-file rewrite hook    (222 lines, bash)
README.md               # user documentation            (392 lines)
LICENSE                 # MIT
.gitignore              # ignores .DS_Store and *.plain.md
```

Observations from the census itself:

- **No application source language.** The entire prior system is two bash scripts. No
  build step, no package manifest, no lockfile, no dependency directory.
- **No tests and no CI.** Nothing under `.github/`, no test harness. The
  substitute for tests is a `STUB` env flag (section 9) that swaps a
  deterministic string for the LLM call so display mechanics can be exercised
  without a model.
- **`.gitignore` ignoring `*.plain.md`** is a direct consequence of the file
  rewriter's default output naming (section 6) — the prior system's own artefacts, if
  produced inside the repo, stay uncommitted.

---

## 3. Integration mechanism

**This is the section a reader must be able to rebuild from. Everything else is
downstream of it.**

The prior system attaches as a **plugin to the harness** and does its work in
**two hooks**: `MessageDisplay` and `PostToolUse`. There is no wrapper process,
no daemon, no socket, no patched binary, and no library import. Each hook fire is
a short-lived subprocess.

### 3.1 The wiring file

`hooks/hooks.json` is the whole attachment, quoted in full and verbatim:

```json
{
  "hooks": {
    "MessageDisplay": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}\"/rewrite.sh",
            "timeout": 60
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}\"/rewrite-md.sh",
            "timeout": 180
          }
        ]
      }
    ]
  }
}
```

Points that matter for a rebuild:

- **`type: "command"`** — the harness spawns the script as a child process. IPC is
  **JSON over stdin/stdout**, one object each way, per fire. Nothing else.
- **`${CLAUDE_PLUGIN_ROOT}`** — harness-supplied env var holding the plugin's
  install directory. The quoting (`"${CLAUDE_PLUGIN_ROOT}"/rewrite.sh`, quotes
  around the variable only, not the whole string) is deliberate: it survives a
  plugin path containing spaces while still letting the shell join the suffix.
- **`matcher: "Write|Edit"`** — a regex against the tool name, the only filtering
  done at registration for the file hook. **There is no path glob.** The script
  itself does the extension check and the directory containment check, and the
  source states this is on purpose, to avoid depending on unverified glob-depth
  semantics in the harness. The authority for "should this file be rewritten"
  lives in the script, not in the config.
- **`MessageDisplay` has no matcher** — it fires for every chunk of every
  assistant message, and the script filters.
- **The two `timeout` values are the outer budget of a nested pair.** 60 s for
  display, 180 s for the file hook. Each script runs its own, strictly smaller,
  LLM client timeout inside that budget (45 s and 150 s, section 9). The gap is
  the point: the LLM call must be the thing that gives up, so the script keeps
  control and can fail open cleanly, rather than being killed mid-write by the
  harness.

### 3.2 Plugin manifest

`.claude-plugin/plugin.json` declares the plugin to the harness. Its shape:

```json
{
  "name": "<plugin>",
  "description": "…",
  "version": "0.1.1-…",
  "author": { "name": "…", "email": "…", "url": "…" },
  "homepage": "…",
  "repository": "…",
  "license": "MIT",
  "keywords": ["ollama", "local-llm", "hooks", "readability", "plain-language", "claude-code"]
}
```

Note there is **no `hooks` key here** — the manifest does not point at
`hooks/hooks.json`. The harness discovers the hooks file by its conventional
location inside the plugin.

### 3.3 Self-hosted marketplace

`.claude-plugin/marketplace.json` lets the repository be added directly as a
plugin marketplace, so install needs no separate registry:

```json
{
  "name": "<owner>-plugins",
  "owner": { "name": "…", "email": "…", "url": "…" },
  "description": "…",
  "plugins": [
    {
      "name": "<plugin>",
      "source": "./",
      "description": "…",
      "category": "productivity"
    }
  ]
}
```

`"source": "./"` is the trick: the marketplace entry points at the repository
root, i.e. at itself.

### 3.4 The `MessageDisplay` event contract

The harness fires `MessageDisplay` **once per streamed chunk**, not once per
message. Each fire is a fresh process. The stdin payload carries:

| Field | Meaning |
|---|---|
| `message_id` | groups the chunks of one assistant message |
| `index` | chunk order, `0,1,2,…` |
| `final` | `true` on the last chunk of the message |
| `delta` | **this chunk's fragment only — not cumulative** |
| `session_id` | current session |
| `transcript_path` | path to the session transcript (JSONL) |
| `cwd` | working directory of the session |

The response, written to stdout, is a single object:

```json
{"hookSpecificOutput":{"hookEventName":"MessageDisplay","displayContent":"…"}}
```

`displayContent` **replaces what this chunk renders**. Emitting nothing (exit 0
with empty stdout) leaves the chunk as-is. Emitting `""` blanks the chunk. Those
three behaviours — replace, leave, blank — are the entire display primitive, and
both display modes are built out of them.

The per-chunk shape forces the central mechanism: **buffer to disk, act on
final.** The script writes each `delta` to a file, and only on `final: true`
does it reassemble the whole message and call the model.

```
chunk 0 (final:false) ─┐
chunk 1 (final:false) ─┤ append delta to $TMPDIR/<plugin>/<session>/<message>/<index>.part
chunk 2 (final:false) ─┘  → emit nothing (append mode) or "" (replace mode)
chunk 3 (final:true)  ──► cat *.part → whole message → one LLM call → emit rewrite
                          → delete the buffer directory
```

The chunk is written with `jq -j` (no trailing newline added) into a file named
with `printf '%08d'`, so the shell glob `"$mdir"/*.part` reassembles in numeric
order under plain lexical sorting.

### 3.5 The `PostToolUse` event contract

Payload fields consumed: `cwd`, `session_id`, and `tool_input.file_path`.

The hook's rewrite output is **not** returned to the harness. The source notes
that `PostToolUse.updatedToolOutput` changes only what the *agent* sees, not the
bytes on disk — so this hook performs the file write itself, through the shell.
Because that write does not go through the agent's `Write` tool, it does not
re-trigger `PostToolUse`: **no recursion loop.**

Its only stdout channel is used for one thing, a one-time diagnostic:

```json
{"systemMessage":"…"}
```

which surfaces a line to the user without blocking the tool and without entering
the agent's context.

### 3.6 Configuration injection path

The hooks are subprocesses, so they inherit the harness process environment. All
tuning is therefore done through the harness's settings `env` block, not by
editing anything in the plugin:

```json
{
  "env": {
    "REWRITE_MODEL": "gemma4:26b-mlx",
    "REWRITE_MODE": "append"
  }
}
```

Three consequences the source calls out explicitly:

1. `env` is **captured at session launch**, so an edit needs a restart.
2. `env` **does not merge across settings scopes** — the highest-precedence file
   that defines `env` supplies the whole block. All variables must live in one
   file.
3. The plugin's own `hooks/hooks.json` lives in a read-only plugin cache and is
   overwritten on update, so it is not a configuration surface.

Because of (1), a second, live control path exists: a **flag file**, re-checked on
every single fire (section 9, `REWRITE_OFF_FILE`).

---

## 4. Data flow — one assistant message, end to end

Trace of a single message in the default (`append`) mode.

**Hop 1 — harness → hook, per chunk.**
Shape: one JSON object on stdin, `{message_id, index, final, delta, session_id,
transcript_path, cwd}`.

**Hop 2 — gate and buffer (`rewrite.sh`, top half).**
In order: master switch, flag-file check, `jq` present, `curl` present, non-empty
payload, `message_id` present. Any failure → exit 0, original renders. Then the
delta is written to
`$TMPDIR/<plugin>/<session_id>/<message_id>/<%08d index>.part`.
Shape at this hop: a fragment of plain text on disk.

**Hop 3 — non-final chunks.**
`append` mode exits 0 → the original streams through normally.
`replace` mode emits `displayContent: ""` → the original is suppressed on screen
while it streams.
This is the only difference between the modes before the final chunk.

**Hop 4 — final chunk: reassembly.**
`full="$(cat "$mdir"/*.part)"` — the complete message text as one string.

**Hop 5 — the prose gate.**
Fenced code blocks are stripped by an `awk` toggle on lines starting with
` ``` `, remaining whitespace is deleted, and the character count is compared to
the floor (200 by default). Below it, the message is not worth rewriting: the
buffer is deleted and the hook fails open — and in `replace` mode it must first
re-emit the whole original, because it already blanked the chunks that carried it.

**Hop 6 — context assembly** (only on this final chunk; see section 5).
Reads `transcript_path` (JSONL) and, if present, `CONTEXT.md` under `cwd`.
Shape: two plain-text blocks folded into the system prompt string.

**Hop 7 — the LLM call.**
Shape: a JSON request body to a local HTTP endpoint; a JSON response back;
`.message.content` extracted as a plain string (section 7).

**Hop 8 — display assembly.**
`append`: `displayContent` = *the final chunk's own delta* + a separator +
the rewrite. The earlier chunks are already on screen, so the reader sees the
whole original followed by the rewrite. The separator is a rule line and a
labelled heading:

```
\n\n────────────────────────\n💬 In plain English:\n\n
```

`replace`: `displayContent` = the rewrite alone, since every earlier chunk was
blanked.

**Hop 9 — emit and clean.**
The assembled string is written to a temp file, the buffer directory is removed,
and the file is handed to `jq --rawfile` to be JSON-encoded into the response
envelope. The temp file is deleted immediately after. Routing the payload through
`--rawfile` rather than a shell variable avoids shell mangling of arbitrary
message text; the explicit delete exists because the opportunistic sweep only
collects directories, so these flat files would otherwise accumulate one per
message.

**Hop 10 — what the human sees.**
The original message, then a rule, then `💬 In plain English:`, then the rewrite.
The transcript on disk and the agent's own context still hold only the original.

**The failure branch of hop 8.** If the rewrite came back empty, the prior system fails
open — and, at most once per session, appends a single diagnostic line explaining
why (section 8). Even that notice only *appends*; it never removes content, so
the fail-open contract survives the diagnostic.

---

## 5. Style system

**There is no style registry.** This is the most important structural fact about
this part of the design, and the easiest thing to over-model when redrawing it.
A style is not a named, stored, selectable object. It is a **hardcoded system
prompt string in each script**, plus two optional context blocks appended to it
at call time.

**Two fixed styles, one per rewriter.**

Display style (`rewrite.sh`), verbatim:

```bash
sys="You rewrite the assistant's message into much simpler, plain English. Keep every fact, name, number, and file path. Use short sentences and everyday words. Leave fenced code blocks unchanged. Output ONLY the rewritten message with no preamble, labels, or commentary."
```

File style (`rewrite-md.sh`), verbatim — same skeleton, extended for a document
rather than a chat message:

```bash
sys="You rewrite Markdown prose into much simpler, plain English. Keep every fact, name, number, link, and file path. Keep all Markdown structure — headings, lists, tables, and links. Do NOT change fenced code blocks or any YAML frontmatter; reproduce them exactly. Use short sentences and everyday words. Output ONLY the rewritten Markdown, with no preamble, labels, or commentary."
```

Both are built from the same four moves: **state the transform**, **enumerate what
must survive verbatim**, **give the style rule**, **forbid preamble**. The last
clause is what makes the response usable as a drop-in string with no parsing.

**Selection.** The only user control over style is binary and coarse:
`REWRITE_CONTEXT=0/1` (send context or not) and `REWRITE_STUB=1` (bypass the
model entirely). Changing the wording of a style means editing the script.

### 5.1 Prompt construction — the display hook

The full prompt is assembled in a fixed order into one system message. The
sections, in the order they are concatenated:

1. the base style instruction (above);
2. the project glossary block, if a glossary file was found;
3. the recent-conversation excerpt, if the transcript was readable;
4. a firewall instruction, present only if 2 or 3 is;
5. a closing re-pitch line, **always last**.

**Project vocabulary.** The hook looks for `CONTEXT.md`, then `docs/CONTEXT.md`,
relative to the payload's `cwd`, and takes a capped prefix:

```bash
doc=""
if [ "$CTX_ON" = "1" ]; then
  for f in "$cwd/CONTEXT.md" "$cwd/docs/CONTEXT.md"; do
    [ -f "$f" ] || continue
    doc="$(jq -Rsr --argjson c "$CTX_DOC_CHARS" \
           'if length > $c then .[0:$c] + "\n\n[… CONTEXT.md truncated]" else . end' \
           "$f" 2>/dev/null)"
    [ -n "$doc" ] && { dbg "context doc: $f chars=${#doc}"; break; }
  done
fi
```

Truncation is done **inside `jq`**, on a string it read with `-Rs`, so the cut
lands on a character boundary rather than mid-codepoint. The same technique is
used for per-message truncation in the excerpt builder.

The glossary and the closing line are then attached:

```bash
repitch="The user doesn't understand. Re-pitch that: give me a little bit of context, talk in Simplified Technical English"
if [ -n "$doc" ]; then
  repitch="$repitch, and use the ubiquitous language from CONTEXT.md."
else
  repitch="$repitch."
fi
[ -n "$doc" ] && sys="$sys"$'\n\n'"The project's CONTEXT.md follows. It defines the ubiquitous language — keep those exact terms in the rewrite."$'\n\n'"$doc"
```

The re-pitch line names the glossary file **only when the file was actually
found** — the prompt never references material that is not in it.

**The conversation excerpt.** Built from the session transcript in one `jq`
program. This is the largest single piece of logic in the prior system, quoted in full
because the excerpt's *shape* is the design:

```bash
convo=""
if [ -n "$tpath" ] && [ -f "$tpath" ] && [ "$CTX_ON" = "1" ]; then
  convo="$(jq -rs --argjson t "$CTX_TURNS" --argjson tm "$CTX_TURN_MSGS" \
                  --argjson c "$CTX_CHARS" --arg mid "$mid" '
    def txt:
      if (.message.content | type) == "string" then .message.content
      else [ .message.content[]? | select(.type == "text") | .text // "" ] | join("\n")
      end;
    def fmt:
      "[" + .role + "] "
      + (.text | if length > $c then .[0:$c] + " […truncated]" else . end);
    def render($current):
      (.[0].role == "user") as $hasu
      | (if $hasu then [ .[0] ] else [] end) as $head
      | (if $hasu then .[1:] else . end) as $rest
      | (if $current
         then (if $tm < 1 then []                    # .[-0:] is .[0:], so 0 needs its own branch
               elif ($rest | length) > $tm then $rest[-$tm:]
               else $rest end)
         else (if ($rest | length) > 1 then $rest[-1:] else $rest end)
         end) as $kept
      | (($rest | length) - ($kept | length)) as $cut
      | { n: (($head | length) + ($kept | length)),
          lines: ( ($head | map(fmt))
                   + (if $cut > 0
                      then [ "[… \($cut) more repl\(if $cut == 1 then "y" else "ies" end) in this exchange, not shown]" ]
                      else [] end)
                   + ($kept | map(fmt)) ) };
    [ .[]
      | select((.type == "user" or .type == "assistant")
               and (.isMeta // false) == false
               and (.isSidechain // false) == false)
      | { role: (.message.role // .type), id: (.message.id // ""), text: txt }
      | select((.text | gsub("[[:space:]]"; "") | length) > 0)
    ]
    | reduce .[] as $m ([];
        if length > 0 and $m.id != "" and .[-1].id == $m.id
        then .[0:-1] + [ .[-1] | .text += "\n" + $m.text ]
        else . + [$m]
        end)
    | map(select(.id != $mid))
    | length as $total
    | [ foreach .[] as $m (0;
          . + (if $m.role == "user" then 1 else 0 end);
          { ex: ., msg: $m }) ]
    | group_by(.ex)
    | map(map(.msg))
    | (if length > ($t + 1) then .[-($t + 1):] else . end)
    | length as $ng
    | [ to_entries[] | . as $e | ($e.value | render($e.key == $ng - 1)) ]
    | ([ .[].n ] | add // 0) as $shown
    | ($total - $shown) as $hidden
    | if $shown == 0 then ""
      else
        "Recent conversation, oldest first. It shows \($shown) of the \($total) messages in this session"
        + (if $hidden > 0 then "; \($hidden) message(s) are not shown" else "" end)
        + ".\n\n"
        + ([ .[].lines[] ] | join("\n\n"))
      end' "$tpath" 2>/dev/null)"
fi
```

Read as a pipeline, it does seven things:

1. **Filter to prose.** Keep only `user`/`assistant` entries, drop meta lines,
   drop sidechain (subagent) lines. Keep only `text` blocks — thinking blocks,
   tool calls, and tool results carry no prose and fall out. Drop anything
   whitespace-only.
2. **Merge by message id.** One assistant turn spans several transcript lines
   sharing `.message.id`; the `reduce` glues consecutive same-id entries back
   into one. A counted "message" is therefore a *turn*, not a log line.
3. **Exclude the message being rewritten** (`.id != $mid`) — it is the payload,
   not context.
4. **Group into exchanges.** A running counter increments at each user message;
   `group_by` turns that into exchanges. An exchange starts at a user message and
   runs to the next one. (The `$hasu` guard handles a leading group that has no
   user message, e.g. a transcript starting mid-stream.)
5. **Window.** Keep the last `turns + 1` exchanges: the current one plus N before it.
6. **Compress asymmetrically.** The **current** exchange keeps its user question
   plus the last `tm` replies. **Older** exchanges keep only their user message
   and their **final** reply. The stated reason: the replies between a question
   and its final answer are tool-step preambles — length without grounding.
7. **Account for every omission.** A header states shown-of-total and how many are
   hidden; each exchange carries an inline `[… N more replies in this exchange,
   not shown]` marker exactly where the cut happened.

**Why anchor on the user's question rather than take the last N messages.** The
source is explicit: a flat window breaks on an agentic turn, where a long run of
tool calls fills the window with assistant status lines and pushes the actual
question out of it entirely. The exchange is the unit that survives that.

**The firewall and the closing line.**

```bash
[ -n "$convo" ] && sys="$sys"$'\n\n'"$convo"
if [ -n "$doc" ] || [ -n "$convo" ]; then
  sys="$sys"$'\n\n'"Use the material above only to understand the message. Do NOT rewrite, answer, or repeat any of it — rewrite only the assistant's message that follows."
fi
# Last, so it sits next to the message it points at.
sys="$sys"$'\n\n'"$repitch"
```

Everything after the base instruction is *reference material*, and the firewall
sentence is what keeps the model from treating the newest question in the excerpt
as a task to answer. It is emitted only when there is material to firewall.

**Role split.** The system message holds style + context + closing instruction.
The **user message holds exactly the reassembled assistant text**, nothing else.
So the thing to be rewritten is unambiguous by position, not by labelling.

**How the response is used.** Directly and unparsed: `.message.content` is
concatenated into `displayContent`. There is no post-processing, no validation,
no retry, no fence-stripping. The "Output ONLY the rewritten message" clause is
the entire output contract.

### 5.2 Prompt construction — the file hook

Much simpler. One system message (the file style above), one user message
containing the file body **with frontmatter already removed**. No conversation
excerpt and no glossary — the file rewriter has no notion of project vocabulary.

---

## 6. The Markdown-file rewriter

Same LLM plumbing, different guards, and it writes to disk — so the guards are
where the design effort went.

**Gate order** (any failure exits 0 and leaves the file exactly as the agent
wrote it):

1. master switch and flag file;
2. **`REWRITE_MD_DIR` must be set** — unset means the whole feature is off;
3. `jq` and `curl` present;
4. `tool_input.file_path` present;
5. **extension guard** — skip `*.plain.md` and `*.<suffix>.md` (its own output,
   preventing self-feeding), require `*.md`, else pass through;
6. **directory containment** — both the file path and the configured directory are
   canonicalised, then the file path must literally be a child of the directory;
7. the file must exist on disk and be readable.

Canonicalisation is done by hand rather than with `realpath`, in a subshell so
the `cd` cannot leak:

```bash
canon() (
  p="$1"
  case "$p" in /*) ;; *) p="$CWD/$p" ;; esac
  d="$(dirname "$p")"; b="$(basename "$p")"
  cd "$d" 2>/dev/null || exit 0
  printf '%s/%s' "$(pwd -P)" "$b"
)
```

`pwd -P` resolves symlinks in the parent, so a symlinked path cannot smuggle a
file past the containment check.

**Frontmatter handling.** If line 1 is `---`, an `awk` pass captures through the
closing `---`; the captured block is held aside verbatim and only the body is
rewritten. If no closing `---` is found, the whole file is treated as body — a
lone `---` is not frontmatter.

**Idempotency.** An HTML-comment marker is written into rewritten files and
checked before rewriting. The check accepts the marker in **two positions** —
first line of the file (an older layout) and first non-blank line of the body —
so files written by an earlier version are still recognised and not chewed twice.
The ordering constraint is real and is why frontmatter is split *before* the
idempotency check: the marker must go **after** the frontmatter, because
frontmatter is only frontmatter when it starts on line 1.

**Output modes.**

| Mode | Target | Content written |
|---|---|---|
| `sibling` (default) | `NAME.<suffix>.md` beside the original | frontmatter (if any) + rewrite |
| `overwrite` | `NAME.md` in place | frontmatter (if any) + marker + rewrite |

**Atomic write.** Always to `"$file_abs.<plugin>.$$.tmp"` first, then `mv -f` onto
the target. A failed temp write or a failed `mv` removes the temp file and fails
open. A partial or empty rewrite is never allowed to land on real content.

---

## 7. The LLM call

Identical in both scripts except for the timeout variable and the prompt.

```bash
req="$(jq -n --arg m "$MODEL" --arg s "$sys" --arg u "$full" \
      '{model:$m,stream:false,think:false,options:{temperature:0.3},messages:[{role:"system",content:$s},{role:"user",content:$u}]}' 2>/dev/null)"
[ -n "$req" ] || { dbg "req build failed"; cleanup; … ; pass_through; }
resp="$(printf '%s' "$req" | curl -sS --max-time "$LLM_TIMEOUT" \
        -H 'Content-Type: application/json' -X POST "$OLLAMA/api/chat" -d @- 2>/dev/null)"
curl_rc=$?
rewrite="$(printf '%s' "$resp" | jq -j '.message.content // empty' 2>/dev/null)"
err="$(printf '%s' "$resp" | jq -r '.error // empty' 2>/dev/null)"
```

**Service.** A local model runner reached over plain HTTP at
`http://localhost:11434` by default, endpoint `POST /api/chat`. There is no SDK
and no client library — `curl` and `jq` are the entire client.

**Model.** A single configurable model name, defaulting to a large local
instruction model (`gemma4:26b-mlx`, roughly 17 GB). One model serves both hooks.

**Streaming.** `"stream": false`. Batch, one request, one response. The display
path could not use streaming anyway: it already has the whole message before it
calls, and it must produce one `displayContent` string.

**`"think": false`.** Reasoning is suppressed explicitly. The stated rationale is
that on a task this mechanical, a hidden reasoning phase spends most of the
latency budget generating tokens the user never sees, for no quality gain.

**Sampling.** `temperature: 0.3` — low, because the task is a faithful restatement.
Nothing else is set: no `top_p`, no seed, no stop sequences.

**Token handling — there is none, by design.** No tokeniser, no token counting, no
`max_tokens`, no context-window arithmetic. Every budget is a **character** cap
applied before the request is built: per-message truncation in the excerpt (800),
the glossary cap (4000), and a minimum-length floor that skips small inputs (200).
The output is unbounded. The source measures the glossary cap in *latency* rather
than tokens — roughly 5 s at 4 000 characters, 8 s at 12 000, 13 s at 29 000 on
one reference machine — treating prompt size as a latency knob, not a capacity one.

**Request construction.** The body is built entirely by `jq -n --arg`, so message
text, glossary text, and transcript text are JSON-escaped by the tool rather than
by string interpolation. Payload delivery is `-d @-` from stdin, which keeps
arbitrarily large bodies off the command line and out of the process table.

**Latency handling.** `--max-time "$LLM_TIMEOUT"`, nested inside the harness hook
timeout with headroom (45 s inside 60 s; 150 s inside 180 s). The display hook
tolerates the full latency because it fires after the message is complete: in
`append` mode the user has already read the original while the model works. In
`replace` mode the latency is visible as a pause before anything appears — which
is why that mode is marked experimental.

**Failure handling.** Two independent signals are read: the `curl` exit code and a
`.error` field in the response body. Together they discriminate four cases:

| Condition | Diagnosis |
|---|---|
| `curl_rc = 28` | client timeout — model too slow for this input |
| `curl_rc ≠ 0` (other) | runner unreachable — not running, refused, DNS |
| `curl_rc = 0`, `.error` matches `not found` | the named model was never pulled |
| `curl_rc = 0`, `.error` set otherwise | runner returned an error verbatim |

A **fifth** case is treated differently on purpose: `curl_rc = 0`, no `.error`, but
an empty completion. That is the model legitimately returning nothing, not a setup
problem, so it fails open **silently** — no notice. Diagnostics are reserved for
conditions the user can actually fix.

**No retry, no backoff, no circuit breaker.** One attempt per message. A dead
runner means every message simply passes through unmodified, at the cost of one
failed connection attempt each. The only memory of failure is the once-per-session
notice flag.

---

## 8. Diagnostics and the once-per-session notice

Both hooks emit at most one setup diagnostic per session, through different
channels because their output contracts differ.

- **Display hook**: appends a line to the on-screen text —
  `⚠️ <plugin>: <why>. Showing the original text unchanged. Shown once per
  session; set REWRITE_NOTICE=0 to silence.` It appends only; it never suppresses,
  so the fail-open contract holds even while diagnosing.
- **File hook**: emits `{"systemMessage": "…"}`, which surfaces to the user without
  blocking the tool and without entering the agent's context.

Each message names the fix — start the runner, pull the model, raise the timeout,
choose a smaller model. The "once" is implemented as a **sentinel file keyed by
session id** (section 10), which is what makes it work at all: every hook fire is
a fresh process with no memory, so the only place session state can live is the
filesystem.

A separate, verbose debug log is available behind `REWRITE_DEBUG=1`, written to
`debug.log` (display) and `debug-md.log` (file). Every gate and decision logs a
line with a timestamp and PID — the PID matters because chunk fires interleave.

---

## 9. Configuration surface

Every knob is an environment variable. The prior system has no config file of its
own.

| Variable | Default | Effect | Used by |
|---|---|---|---|
| `REWRITE_ENABLED` | `1` | Master switch. `0` passes everything through. Read at session launch only. | both |
| `REWRITE_OFF_FILE` | `~/.claude/<plugin>-off` | Path to a flag file. **While the file exists, rewrites pause.** Re-checked on every fire, so it works mid-session where env vars cannot. | both |
| `REWRITE_MODE` | `append` | `append` or `replace` — display strategy. | display |
| `REWRITE_MODEL` | `gemma4:26b-mlx` | Model tag on the local runner. | both |
| `REWRITE_OLLAMA` | `http://localhost:11434` | Runner base URL. | both |
| `REWRITE_MIN_CHARS` | `200` | Skip inputs whose prose (code stripped) is shorter. | both |
| `REWRITE_CONTEXT` | `1` | `1` sends conversation excerpt + glossary; `0` sends the message alone. | display |
| `REWRITE_CONTEXT_TURNS` | `5` | Exchanges before the current one, each compressed to its question and final reply. | display |
| `REWRITE_CONTEXT_TURN_MSGS` | `3` | Replies kept from the **current** exchange, newest first. The question itself is always kept. | display |
| `REWRITE_CONTEXT_CHARS` | `800` | Per-message truncation inside the excerpt. | display |
| `REWRITE_CONTEXT_DOC_CHARS` | `4000` | Cap on the glossary excerpt. Costs latency directly. | display |
| `REWRITE_STUB` | `0` | `1` substitutes a deterministic string for the LLM call — tests display mechanics with no model. | both |
| `REWRITE_TIMEOUT` | `45` | LLM client timeout, display hook. Must stay under the 60 s hook timeout. | display |
| `REWRITE_MD_TIMEOUT` | `150` | LLM client timeout, file hook. Must stay under the 180 s hook timeout. | file |
| `REWRITE_DEBUG` | `0` | `1` writes a debug log. | both |
| `REWRITE_NOTICE` | `1` | `1` shows the once-per-session setup diagnostic; `0` is fully silent. | both |
| `REWRITE_MD_DIR` | *(unset)* | **Opt-in for the file hook.** Only `*.md` resolving inside this directory is rewritten. Unset = the file hook is inert. | file |
| `REWRITE_MD_MODE` | `sibling` | `sibling` or `overwrite`. | file |
| `REWRITE_MD_SUFFIX` | `plain` | Sibling infix: `NAME.<suffix>.md`. | file |

Plus the two hook timeouts in `hooks/hooks.json` (60 s and 180 s) — editable in
principle, but the file lives in a read-only, update-overwritten plugin cache, so
in practice they are fixed ceilings the env timeouts must respect.

**Input validation.** Every value that reaches `jq` as `--argjson` (i.e. as a JSON
number) is validated first, because a non-numeric value there would be a syntax
error rather than a bad result:

```bash
case "$CTX_ON"        in 0|1) ;; *) CTX_ON=1        ;; esac
case "$CTX_TURNS"     in ''|*[!0-9]*) CTX_TURNS=5   ;; esac
case "$CTX_TURN_MSGS" in ''|*[!0-9]*) CTX_TURN_MSGS=3 ;; esac
case "$CTX_CHARS"     in ''|*[!0-9]*) CTX_CHARS=800 ;; esac
case "$CTX_DOC_CHARS" in ''|*[!0-9]*) CTX_DOC_CHARS=4000 ;; esac
```

Bad input silently reverts to the default rather than failing — consistent with
the fail-open posture.

**Three control planes, at three different latencies:** the plugin
enable/disable (next session), `REWRITE_ENABLED` (next session), and the flag file
(next message). The flag file exists precisely because the other two are frozen at
launch, and the source suggests binding a two-line toggle script to a hotkey,
which flips every running session at once.

---

## 10. State and persistence

The prior system is **stateless in process** — every hook fire is a new process with no
memory — so all state is files under `$TMPDIR/<plugin>/` (falling back to `/tmp`),
plus one user-created flag file.

| Path | Format | Lifetime | Purpose |
|---|---|---|---|
| `$TMPDIR/<plugin>/<session_id>/<message_id>/<%08d>.part` | raw text fragment | one message | the chunk buffer; the prior system's only real data structure |
| `$TMPDIR/<plugin>/<session_id>.notified` | empty sentinel | one session | display-hook notice already shown |
| `$TMPDIR/<plugin>/<session_id>.md-notified` | empty sentinel | one session | file-hook notice already shown |
| `$TMPDIR/<plugin>/<session_id>.<message_id>.out` | raw text | milliseconds | assembled `displayContent`, deleted right after encoding |
| `$TMPDIR/<plugin>/<session_id>.<message_id>.notice` | raw text | milliseconds | same, for the diagnostic path |
| `$TMPDIR/<plugin>/<session_id>/<message_id>.orig` | raw text | milliseconds | original text re-shown in `replace` mode on failure |
| `$TMPDIR/<plugin>/debug.log`, `debug-md.log` | timestamped text lines | until deleted | debug tracing, off by default |
| `~/.claude/<plugin>-off` (configurable) | existence only | user-controlled | runtime pause |
| `<file>.<plugin>.$$.tmp` beside the target | Markdown | milliseconds | staging for the atomic file write |

**Two-level directory keying** (`<session>/<message>/`) is what makes concurrent
sessions and interleaved messages safe: each message's chunks land in their own
directory, and the process id in the temp filename separates concurrent file
writes.

**Garbage collection is opportunistic**, piggybacked on every display-hook fire:

```bash
find "$BUF_ROOT" -mindepth 2 -maxdepth 2 -type d -mmin +30 -exec rm -rf {} + 2>/dev/null || true
find "$BUF_ROOT" -mindepth 1 -maxdepth 1 -type d -empty -mmin +30 -exec rmdir {} + 2>/dev/null || true
```

First sweep: message directories abandoned mid-stream (a session killed before a
`final` chunk) older than 30 minutes. Second sweep: session directories left empty
behind them. There is no daemon and no cleanup on exit; the depth bounds keep the
sweep cheap.

The flat files (`.out`, `.notice`, `.notified`) are **not** covered by the sweep —
which is why `emit()` deletes its own input file inline, and why the sentinels are
left to the operating system's temp-directory policy.

**The prior system persists nothing outside temp** except, in the file hook's case, the
rewritten Markdown itself. No database, no cache of rewrites, no history.

---

## 11. External dependencies

**No package dependencies.** No manifest, no lockfile, no vendored code. Every
dependency is a program expected on `PATH` or a service expected on a port.

| Dependency | Kind | Used for | If missing |
|---|---|---|---|
| `bash` | shell | both scripts; `set -uo pipefail` | hooks do not run |
| `jq` | binary | every JSON parse, every JSON build, safe string truncation, transcript processing | checked explicitly → fail open |
| `curl` | binary | the only HTTP client; timeout enforcement via `--max-time` | checked explicitly → fail open |
| `awk` | binary | stripping fenced code for the length gate; splitting YAML frontmatter | not checked |
| `sed` | binary | first non-blank line of the body, for the idempotency check | not checked |
| coreutils / shell builtins | binaries | `cat`, `printf`, `tr`, `wc`, `ls`, `head`, `find`, `date`, `dirname`, `basename`, `mv`, `rm`, `mkdir`, `pwd` | not checked |
| a local model runner | **service**, HTTP on `localhost:11434` | the rewriting itself | fail open + one-time notice |
| a pulled model | model weights on that service | the rewriter | fail open + one-time notice |
| the agent harness | host process | supplies the hook events, the payloads, `${CLAUDE_PLUGIN_ROOT}`, and the process environment | nothing runs |

**Egress.** All inference is local; no conversation content leaves the machine.
What is sent to the local endpoint on each display call is: the assistant message,
the conversation excerpt, and the glossary excerpt. Tool results and file contents
are filtered out of the excerpt — though a message may of course quote them. The
one way to change this is pointing the base URL at a remote endpoint, which would
send all of the above off-box; the source flags this explicitly as a decision the
user must make knowingly.

---

## 12. Design decisions worth carrying forward

1. **Fail open is a structural property, not a policy.** Every early exit is
   `exit 0` with empty stdout, and empty stdout means "leave it alone" in the
   harness contract. The safe path is also the cheapest path, so it cannot rot.
2. **Buffer-to-final is forced by the event granularity.** A per-chunk event and a
   whole-message transform meet only through disk, because each fire is a separate
   process with no shared memory.
3. **The two display modes are built from one primitive.** Replace, leave, blank.
   `append` never blanks; `replace` blanks everything but the last chunk. Every
   failure path in `replace` mode must therefore *restore* the original, and every
   such path in the script does exactly that — the asymmetry is the mode's whole
   cost.
4. **Guards live in the script, not in the registration.** The `PostToolUse`
   matcher is deliberately coarse; extension and containment checks are done in
   code, where their semantics are known and testable.
5. **Character caps instead of token budgets.** Crude, dependency-free, and tuned
   against measured latency rather than a context window.
6. **Context is quantified, not merely truncated.** The excerpt tells the model how
   much it is not seeing, in the header and inline at each cut — so the model is
   never left to assume the excerpt is the whole conversation.
7. **The exchange, not the message, is the context unit.** Anchoring on the user's
   question is what makes the excerpt survive agentic turns full of tool output.
8. **Diagnose only what the user can fix.** An empty completion from a healthy
   runner is silent; an unreachable runner, a timeout, and a missing model each get
   one named fix, once per session.
9. **Honest limits in the documentation.** The README records that prompt-position
   variants tested identically (20 of 20 runs both ways) and declines to claim the
   change fixed anything — the ordering is documented as layout preference, not as
   a fix.

## 13. Known limits

- The "leave fenced code unchanged" rule is a prompt instruction, not a parser
  guarantee; a weak model can still mangle code.
- `overwrite` mode replaces real documents with model output, guarded only by the
  idempotency marker and the atomic write.
- Large files are slow — at roughly 60 tokens/s, a long document can take 30–120 s,
  which is why the file hook's budget is triple the display hook's.
- No retries: a transient failure simply means that one message is not rewritten.
- Everything hangs on undocumented-to-the-reader harness payload fields; a change
  to the event shape degrades the prior system to a permanent no-op — silently, and by
  design.
