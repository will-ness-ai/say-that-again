"""Run the run-01 corpus through the real pipeline, then score it with the run-01 check.

Run 01 used fresh frontier agents. This runs the same four samples through the inference
source that ADR 0007 chose, so the 117/117 result can be tested against the thing we ship.

    python3 docs/prototypes/run-02/bench.py --model anthropic/claude-haiku-4.5 --style plain

Writes the translations to out/<tag>/ and one row per sample to out/<tag>/result.json.
"""

import argparse
import concurrent.futures
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN01 = os.path.join(HERE, "..", "run-01")
sys.path.insert(0, HERE)
sys.path.insert(0, RUN01)

import check  # noqa: E402  the run-01 fidelity check, unchanged
import pipeline  # noqa: E402


def tag_of(model, style):
    return f"{model.replace('/', '-')}.{style}"


def cost_of(usage):
    return float(usage.get("cost") or 0.0)


def cached_of(usage):
    details = usage.get("prompt_tokens_details") or {}
    return int(details.get("cached_tokens") or 0)


CONTEXTS = json.load(open(os.path.join(HERE, "context.json")))


def one(name, original, style, model, key):
    result = pipeline.run(original, style, model, key, turns=CONTEXTS.get(name))
    result["name"] = name
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=pipeline.DEFAULT_MODEL)
    parser.add_argument("--style", default="plain")
    parser.add_argument("--repeat", type=int, default=1,
                        help="run the corpus N times, to test whether the cache warms")
    args = parser.parse_args()

    samples = json.load(open(os.path.join(RUN01, "samples.json")))
    style = pipeline.load_style(args.style)
    key = pipeline.load_key()
    tag = tag_of(args.model, args.style)
    out = os.path.join(HERE, "out", tag)
    os.makedirs(out, exist_ok=True)

    results = []
    for pass_number in range(args.repeat):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(one, name, samples[name]["text"], style, args.model, key): name
                for name in sorted(samples)
            }
            for future in concurrent.futures.as_completed(futures):
                record = future.result()
                record["pass"] = pass_number
                results.append(record)

    results.sort(key=lambda r: (r["pass"], r["name"]))
    total = failed = 0
    rows = []
    for record in results:
        name = record["name"]
        original = samples[name]["text"]
        translation = record["translation"]
        suffix = "" if record["pass"] == 0 else f".p{record['pass']}"
        open(os.path.join(out, f"{name}{suffix}.translation.md"), "w").write(translation)
        open(os.path.join(out, f"{name}{suffix}.diagrams.md"), "w").write(record["diagrams"])
        checks = check.run(original, translation) if translation else []
        bad = [c for c in checks if not c[2]]
        total += len(checks)
        failed += len(bad)
        cost = cost_of(record["usage"]["call1"]) + cost_of(record["usage"]["call2"])
        cached = cached_of(record["usage"]["call1"]) + cached_of(record["usage"]["call2"])
        prompt_tokens = sum(int((record["usage"][c] or {}).get("prompt_tokens") or 0)
                            for c in ("call1", "call2"))
        rows.append({
            "name": name, "pass": record["pass"], "pass_count": len(checks) - len(bad),
            "check_count": len(checks), "missing": [(c[0], c[1]) for c in bad],
            "chars_in": len(original), "chars_out": len(translation),
            "context_chars": record.get("context_chars", 0),
            "seconds": round(record["seconds"].get("total", 0), 1),
            "cost_usd": round(cost, 6), "prompt_tokens": prompt_tokens,
            "cached_tokens": cached, "diagram_chars": len(record["diagrams"]),
            "failure": record["failure"],
        })
        grew = (len(translation) / len(original) * 100 - 100) if translation else 0
        print(f"### {name} p{record['pass']}  {len(checks) - len(bad)}/{len(checks)} pass"
              f"   {len(original)} -> {len(translation)} chars ({grew:+.0f}%)"
              f"   {record['seconds'].get('total', 0):.1f}s"
              f"   ${cost:.5f}   cached {cached}/{prompt_tokens} tok"
              f"   {record['failure'] or ''}")
        for kind, label, _ in bad:
            print(f"    MISSING  {kind:12} {label!r}")

    summary = {
        "model": args.model, "style": args.style, "rows": rows,
        "checks": total, "failures": failed,
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
    }
    json.dump(summary, open(os.path.join(out, "result.json"), "w"), indent=2)
    print(f"\n{total - failed}/{total} checks pass. {failed} failures."
          f"  ${summary['cost_usd']:.5f} total.")


if __name__ == "__main__":
    main()
