"""The translation pipeline: the gate, call 1, call 2, and the inference source.

The sidecar and the bench both import this module, so the run against a live harness
and the run against the saved corpus use the same code.

Design: ADR 0002 (the gate), ADR 0004 (two calls), ADR 0007 (one model through
OpenRouter). Request shape: docs/design/inference.md.
"""

import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
GATE_CHARS = 200
DEFAULT_MODEL = "anthropic/claude-haiku-4.5"

# In the repository the skills live under docs/prompts/vendor. An install copies them next to
# this file instead, so both places are tried.
VENDOR_DIRS = (os.path.join(HERE, "..", "..", "prompts", "vendor"),
               os.path.join(HERE, "prompts", "vendor"))


def vendored(name):
    """A third-party skill, word for word. See docs/prompts/vendor/README.md."""
    for directory in VENDOR_DIRS:
        path = os.path.join(directory, name)
        if os.path.exists(path):
            return open(path).read().strip()
    raise FileNotFoundError(f"{name} is in none of {VENDOR_DIRS}")


# Call 1 is machinery. A style switches it on or off; a style does not change its text.
# Source: docs/prompts/diagram.md.
DIAGRAM_ROLE = """You are a technical writer. A software agent has answered a developer, and the
answer is hard to follow. You help that developer understand it, by drawing the parts of the
answer that a picture carries better than prose.

You draw only what the answer already states. You cannot read the repository, so each path,
name, and step you draw comes from the text itself."""

# The `show-me` skill, word for word. Its forms are the whole job of this call.
DIAGRAM_JOB = vendored("show-me.SKILL.md")

DIAGRAM_FORMAT = """Write nothing but diagrams. Give each one a fenced block, and one line
directly above the fence that names its point and how it lands:

  replaces: <the point it covers>    the diagram carries that point completely, and holds every
                                     fact of the prose it covers, so that prose can go.

  supplements: <the point it covers> the diagram illustrates a point that the prose must still
                                     make in words.

Most answers need no picture. Return nothing when no view makes the answer clearer. That is a
correct answer."""

# The `stop-slop` skill, word for word. It rides with every style.
STOP_SLOP = vendored("stop-slop.SKILL.md")

DIAGRAM_INSTRUCTION = "Draw the answer in <text-block>.\nUse <context> to understand it."
TRANSLATE_INSTRUCTION = ("Translate the answer in <text-block>.\n"
                         "Use <context> and <diagrams> to understand it.")
CONTEXT_TURNS = 5
CONTEXT_CHARS = 600


class CallFailure(Exception):
    """A model call did not return content. `cls` names the failure class."""

    def __init__(self, cls, detail=""):
        super().__init__(f"{cls}: {detail}" if detail else cls)
        self.cls = cls
        self.detail = detail


def load_key():
    """The key from the environment, else from a .env file beside the repository root."""
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    for depth in range(0, 7):
        path = os.path.join(HERE, *([".."] * depth), ".env")
        if os.path.exists(path):
            for line in open(path):
                name, _, value = line.partition("=")
                if name.strip() == "OPENROUTER_API_KEY" and value.strip():
                    return value.strip()
    raise CallFailure("no key", "OPENROUTER_API_KEY is not set and no .env holds it")


def load_style(name="plain"):
    path = name if os.path.sep in name else os.path.join(HERE, "styles", f"{name}.json")
    return json.load(open(path))


def passes_gate(text_block):
    return len(text_block) > GATE_CHARS


def system_message(role, job, **blocks):
    """The constant half of a prompt. It does not change between text blocks."""
    parts = [f"<role>\n{role}\n</role>", f"<job>\n{job}\n</job>"]
    for name, body in blocks.items():
        if body:
            tag = name.replace("_", "-")
            parts.append(f"<{tag}>\n{body}\n</{tag}>")
    return "\n\n".join(parts)


def context_block(turns):
    """The tail of the conversation, as the model reads it.

    `turns` is a list of (role, text) pairs, oldest first. The last CONTEXT_TURNS exchanges
    survive, and each turn is cut to CONTEXT_CHARS so that one long answer upstream cannot
    crowd out the block it is meant to explain.
    """
    if not turns:
        return ""
    kept = turns[-(CONTEXT_TURNS * 2):]
    lines = []
    for role, text in kept:
        text = " ".join(text.split())
        if len(text) > CONTEXT_CHARS:
            text = text[:CONTEXT_CHARS].rstrip() + " …"
        lines.append(f"{role}: {text}")
    return "\n\n".join(lines)


def call(model, system, user, key, timeout=90):
    """One model call. Returns (content, usage, seconds). Raises CallFailure."""
    system_part = {"type": "text", "text": system}
    if model.startswith("anthropic/"):
        # Anthropic caching is explicit. Below the model's minimum prefix it does nothing,
        # silently. Send it anyway, and let the usage numbers report what happened.
        system_part["cache_control"] = {"type": "ephemeral"}

    body = {
        "model": model,
        "stream": False,
        "temperature": 0.2,
        "reasoning": {"enabled": False},
        "usage": {"include": True},
        "messages": [
            {"role": "system", "content": [system_part]},
            {"role": "user", "content": user},
        ],
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            answer = json.load(response)
    except urllib.error.HTTPError as error:
        cls = "rate limit" if error.code == 429 else "http error"
        raise CallFailure(cls, f"{error.code} {error.read()[:200]!r}")
    except urllib.error.URLError as error:
        cls = "timeout" if "timed out" in str(error.reason) else "unreachable"
        raise CallFailure(cls, str(error.reason))
    except TimeoutError:
        raise CallFailure("timeout", f"{timeout}s")
    seconds = time.time() - started

    choices = answer.get("choices") or []
    content = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
    usage = answer.get("usage") or {}
    if not content:
        raise CallFailure("refusal", "200 with empty content")
    return content, usage, seconds


def draw(text_block, style, model, key, timeout=90, context=""):
    """Call 1. An empty answer is a correct result, not a fault.

    Whatever comes back goes to call 2 whole. Nothing reads or filters it in between - call 2
    holds both the original and this answer, so it decides which parts are pictures and which
    are worth placing.
    """
    system = system_message(DIAGRAM_ROLE, DIAGRAM_JOB, output_format=DIAGRAM_FORMAT)
    user = (f"{DIAGRAM_INSTRUCTION}\n\n<context>\n{context}\n</context>"
            f"\n\n<text-block>\n{text_block}\n</text-block>")
    try:
        return call(model, system, user, key, timeout)
    except CallFailure as failure:
        if failure.cls == "refusal":
            return "", {}, 0.0
        raise


def translate(text_block, diagrams, style, model, key, timeout=90, context=""):
    """Call 2. It holds the original, the context, the diagrams, and the pen."""
    system = system_message(style["role"], style["job"], stop_slop=STOP_SLOP)
    user = (f"{TRANSLATE_INSTRUCTION}\n\n<context>\n{context}\n</context>"
            f"\n\n<text-block>\n{text_block}\n</text-block>"
            f"\n\n<diagrams>\n{diagrams}\n</diagrams>")
    return call(model, system, user, key, timeout)


def run(text_block, style, model=DEFAULT_MODEL, key=None, budget=110.0, turns=None):
    """The whole pipeline for one text block. Returns a record of what happened."""
    key = key or load_key()
    context = context_block(turns or [])
    record = {
        "model": model,
        "style": style["name"],
        "chars_in": len(text_block),
        "context_chars": len(context),
        "diagrams": "",
        "translation": "",
        "failure": None,
        "seconds": {"call1": 0.0, "call2": 0.0},
        "usage": {"call1": {}, "call2": {}},
    }
    started = time.time()

    if style.get("diagrams") == "on":
        try:
            drawing, usage, seconds = draw(text_block, style, model, key, context=context)
            record["diagrams"] = drawing
            record["usage"]["call1"] = usage
            record["seconds"]["call1"] = seconds
        except CallFailure as failure:
            # A translation with no picture is still correct. Call 2 goes on.
            record["failure"] = f"call1 {failure.cls}"

    left = budget - (time.time() - started)
    if left <= 5:
        record["failure"] = "timeout: no budget left for call 2"
        return record

    try:
        text, usage, seconds = translate(text_block, record["diagrams"], style, model, key,
                                         left, context=context)
        record["translation"] = text
        record["usage"]["call2"] = usage
        record["seconds"]["call2"] = seconds
    except CallFailure as failure:
        record["failure"] = f"call2 {failure.cls}"
    record["chars_out"] = len(record["translation"])
    record["seconds"]["total"] = time.time() - started
    return record
