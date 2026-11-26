#!/usr/bin/env bash
# PreToolUse hook on Bash: block commands that write into data/raw/.
#
# The deny list in settings.json covers the Write and Edit tools only, so
# `cp x data/raw/bike_daily.csv` from Bash is seeded fault 4. This hook
# looks for the common write forms -- cp / mv / install destinations,
# tee targets, and > / >> redirections -- whose target resolves into
# data/raw/, and exits 2 so the command never runs. Reading from data/raw/
# is allowed.
#
# It is a pattern match, not a sandbox: a path built from a variable, a
# `python -c` write, or a script that writes the file will get past it.
# RAW_SHA256 and tests/test_contract.py::test_raw_csv_is_unmodified are the
# backstop for every route this misses.
set -uo pipefail

python3 -c '
import json, os, re, shlex, sys

payload = json.load(sys.stdin)
command = payload.get("tool_input", {}).get("command", "")
cwd = payload.get("cwd") or os.getcwd()
project = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
raw_dir = os.path.realpath(os.path.join(project, "data", "raw"))


def into_raw(path, here):
    if not path or path.startswith("&"):
        return False
    full = os.path.realpath(os.path.join(here, os.path.expanduser(path)))
    # Also refuse any path that names a data/raw directory, wherever it is.
    return full == raw_dir or full.startswith(raw_dir + os.sep) or "data/raw" in path


hits = []
here = cwd
for segment in re.split(r"&&|\|\||;|\||\n", command):
    for target in re.findall(r"\d?>>?\s*([^\s;&|<>]+)", segment):
        if into_raw(target, here):
            hits.append(f"redirect > {target}")
    try:
        words = shlex.split(segment)
    except ValueError:
        words = segment.split()
    while words and ("=" in words[0] and not words[0].startswith("-") or words[0] in ("sudo", "command", "env")):
        words = words[1:]
    if not words:
        continue
    prog, args = os.path.basename(words[0]), words[1:]
    args = [a for a in args if not re.match(r"\d?>>?", a)]
    if prog == "cd" and args:
        here = os.path.realpath(os.path.join(here, os.path.expanduser(args[0])))
    elif prog in ("cp", "mv", "install", "rsync", "ln"):
        dests = [args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-t", "--target-directory")]
        operands = [a for a in args if not a.startswith("-")]
        if operands:
            dests.append(operands[-1])
        hits += [f"{prog} -> {d}" for d in dests if into_raw(d, here)]
    elif prog == "tee":
        hits += [f"tee -> {a}" for a in args if not a.startswith("-") and into_raw(a, here)]

if hits:
    print("BLOCKED by .claude/hooks/protect_raw.sh: this Bash command writes into "
          "data/raw/, which is read-only (CLAUDE.md; seeded fault 4).", file=sys.stderr)
    for h in hits:
        print(f"  write target: {h}", file=sys.stderr)
    print("  The raw CSV is pinned by RAW_SHA256. Write derived data under data/processed/.",
          file=sys.stderr)
    sys.exit(2)
'
