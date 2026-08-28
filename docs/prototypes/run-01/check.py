"""The cheap fidelity check. Deterministic, and it makes no model call.

Pulls out of the original the items that a translation must keep byte for byte,
then tests that the translation holds each one.

    python3 docs/prototypes/run-01/check.py
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLES = json.load(open(os.path.join(HERE, "samples.json")))

FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
TICK = re.compile(r"`([^`\n]+)`")
LABEL = re.compile(r"\bQ\d+\b|#\d+|\bOption [A-Z]\b")
LISTNUM = re.compile(r"^\s*(\d+)[\.\)]\s", re.M)
NUM = re.compile(r"(?<![\w#])(\d+(?:\.\d+)?)(?![\w])")

# Negation counting is measured here to show that it fails. See finding 3.
NEG = re.compile(r"\b(not|never|cannot|can't|don't|won't|no|without|nothing)\b", re.I)

# List markers that every document holds. They carry no fact of their own.
STOP = {"0", "1", "2", "3", "4", "5"}

VARIANTS = [("translation", "paired"), ("translation-no-context", "bare")]


def fences(text):
    return [b.strip() for b in FENCE.findall(text) if b.strip()]


def items(original):
    """Every item the translation must hold, as (kind, needle, label)."""
    out = []
    for block in fences(original):
        out.append(("code block", block, block.splitlines()[0][:44]))
    for tick in sorted(set(TICK.findall(original))):
        out.append(("backtick", tick, tick[:44]))
    for label in sorted(set(LABEL.findall(original))):
        out.append(("label", label, label))
    for n in sorted(set(LISTNUM.findall(original))):
        out.append(("list number", n + ".", n + "."))
    for n in sorted(set(NUM.findall(original)) - STOP):
        out.append(("number", n, n))
    return out


def run(original, translation):
    rows = [(kind, label, needle in translation) for kind, needle, label in items(original)]
    if original.rstrip().endswith("?"):
        rows.append(("ask", "original ends with a question", translation.rstrip().endswith("?")))
    return rows


def main():
    total = failed = 0
    for name in sorted(SAMPLES):
        original = SAMPLES[name]["text"]
        for suffix, tag in VARIANTS:
            path = os.path.join(HERE, "samples", f"{name}.{suffix}.md")
            if not os.path.exists(path):
                continue
            translation = open(path).read()
            rows = run(original, translation)
            bad = [r for r in rows if not r[2]]
            total += len(rows)
            failed += len(bad)
            grew = len(translation) / len(original) * 100 - 100
            print(f"\n### {name}.{tag}   {len(rows) - len(bad)}/{len(rows)} pass"
                  f"   {len(original)} -> {len(translation)} chars ({grew:+.0f}%)"
                  f"   negation words {len(NEG.findall(original))} -> {len(NEG.findall(translation))}")
            for kind, label, _ in bad:
                print(f"    MISSING  {kind:12} {label!r}")
    print(f"\n{total - failed}/{total} checks pass. {failed} failures.")


if __name__ == "__main__":
    main()
