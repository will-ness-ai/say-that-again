"""Can the sidecar find out that its work will be thrown away, before it spends a call?

Probe P3 showed the harness discards a MessageDisplay answer under `verbose` and tells the
hook nothing. This module looks for the discard modes from inside the hook process. It reads
only what a hook can read: its own environment, the harness command line, and the settings
and plugin files on disk.

`inspect()` returns a dict. `verdict` is one of:
  clear   - no discard mode found
  race    - a second MessageDisplay hook is installed, and the last answer wins
  discard - a mode was found that throws the answer away

A settings file is not the only place a MessageDisplay hook comes from. An enabled plugin
registers one too, and that hook does not appear in any settings file. See the run-02 report.
"""

import glob
import json
import os
import subprocess

MODES = ("verbose", "disableAllHooks", "allowManagedHooksOnly")
PLUGIN_CACHE = os.path.expanduser("~/.claude/plugins/cache")


def harness_argv():
    """The command line of the harness process, found by walking up from this process."""
    pid = os.getppid()
    for _ in range(12):
        if pid <= 1:
            break
        try:
            out = subprocess.run(
                ["ps", "-o", "ppid=,args=", "-p", str(pid)],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
        except Exception:
            return []
        if not out:
            break
        parent, _, args = out.partition(" ")
        if "claude" in args and "--settings" in args:
            return args.split()
        try:
            pid = int(parent)
        except ValueError:
            break
    return []


def settings_files(cwd, argv):
    """Every settings file this run can read, weakest first."""
    paths = [
        os.path.expanduser("~/.claude/settings.json"),
        os.path.join(cwd, ".claude", "settings.json"),
        os.path.join(cwd, ".claude", "settings.local.json"),
    ]
    if "--settings" in argv:
        index = argv.index("--settings") + 1
        if index < len(argv):
            paths.append(argv[index])
    return [p for p in paths if p and os.path.exists(p)]


def count_display_hooks(data):
    entries = (data.get("hooks") or {}).get("MessageDisplay") or []
    return sum(len(entry.get("hooks") or []) for entry in entries)


def plugin_display_hooks(enabled):
    """MessageDisplay hooks that come from an enabled plugin, not from a settings file."""
    total = 0
    for name, on in (enabled or {}).items():
        if not on or "@" not in name:
            continue
        plugin, _, marketplace = name.partition("@")
        pattern = os.path.join(PLUGIN_CACHE, marketplace, plugin, "*", "hooks", "hooks.json")
        seen = set()
        for path in sorted(glob.glob(pattern)):
            try:
                found = count_display_hooks(json.load(open(path)))
            except Exception:
                continue
            if found:
                # One plugin registers one set of hooks, whatever versions sit in the cache.
                seen.add(plugin)
        total += len(seen)
    return total


def inspect(payload):
    """Look for every discard mode the hook can see."""
    cwd = payload.get("cwd") or os.getcwd()
    argv = harness_argv()
    found = {}

    if "--verbose" in argv or "-v" in argv:
        found["verbose"] = "harness command line"

    display_hooks = 0
    enabled = {}
    for path in settings_files(cwd, argv):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for mode in MODES:
            if data.get(mode):
                found[mode] = path
        display_hooks += count_display_hooks(data)
        enabled.update(data.get("enabledPlugins") or {})

    if not found.get("disableAllHooks"):
        display_hooks += plugin_display_hooks(enabled)

    verdict = "clear"
    if display_hooks > 1:
        verdict = "race"
    if found:
        verdict = "discard"

    return {
        "verdict": verdict,
        "found": found,
        "display_hooks": display_hooks,
        "entrypoint": os.environ.get("CLAUDE_CODE_ENTRYPOINT", ""),
        "argv_seen": bool(argv),
    }


if __name__ == "__main__":
    import sys

    print(json.dumps(inspect(json.load(sys.stdin)), indent=2))
