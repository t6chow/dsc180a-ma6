"""The PreToolUse hook that keeps Bash out of data/raw/ (seeded fault 4).

Each case feeds the hook the JSON payload Claude Code sends and checks the
exit code: 2 blocks the command, 0 lets it run.
"""
import json
import subprocess

import pytest

from src.config import ROOT

HOOK = ROOT / ".claude" / "hooks" / "protect_raw.sh"


def run_hook(command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(ROOT)})
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, capture_output=True, text=True,
        env={"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"},
    )


@pytest.mark.parametrize("command", [
    "cp /tmp/x.csv data/raw/bike_daily.csv",
    "mv new.csv data/raw/",
    "echo hi > data/raw/bike_daily.csv",
    "echo hi >>data/raw/notes.txt",
    "cat x | tee data/raw/bike_daily.csv",
    "cd data && cp ../x.csv raw/bike_daily.csv",
    f"cp -t {ROOT}/data/raw x.csv",
    "cp x.csv ./data/raw/../raw/y.csv",
])
def test_writes_into_raw_are_blocked(command):
    result = run_hook(command)
    assert result.returncode == 2, f"not blocked: {command}"
    assert "BLOCKED" in result.stderr


@pytest.mark.parametrize("command", [
    "cp data/raw/bike_daily.csv /tmp/copy.csv",
    "cat data/raw/bike_daily.csv > /tmp/out.csv",
    "head data/raw/bike_daily.csv 2>&1",
    "shasum -a 256 data/raw/bike_daily.csv",
    "make test",
    "grep -c , data/raw/bike_daily.csv | tee /tmp/n.txt",
])
def test_reads_and_other_commands_are_allowed(command):
    result = run_hook(command)
    assert result.returncode == 0, f"wrongly blocked: {command}\n{result.stderr}"
