"""Answer one MessageDisplay delta.

SEAM_MODE selects the behaviour under test:
  append  - return the final delta plus a marker (the ADR 0006 construction)
  crash   - exit non-zero on the final delta, to test the fail-open contract
  garbage - print text that is not JSON
"""

import json
import os
import sys

payload = json.load(sys.stdin)
if not payload.get("final"):
    sys.exit(0)

mode = os.environ.get("SEAM_MODE", "append")

if mode == "crash":
    sys.stderr.write("simulated translation failure\n")
    sys.exit(1)

if mode == "garbage":
    print("this is not json")
    sys.exit(0)

delta = payload.get("delta", "")
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "MessageDisplay",
        "displayContent": delta + "\n\n[[APPENDED-TRANSLATION]]",
    }
}))
