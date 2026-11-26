---
name: run-pipeline
description: Run the full pipeline on HEAD and on a baseline commit, then report the validation-only delta for all four models. Use whenever someone asks what a change did to the scores, or for a before/after comparison.
allowed-tools: Read, Bash(git worktree*), Bash(git rev-parse*), Bash(git status*), Bash(make*), Bash(python .claude/skills/run-pipeline/delta.py*)
---

# Current state

!`git log --oneline -1 && git status --short`

# Validation delta: HEAD vs $ARGUMENTS

`$ARGUMENTS` is the baseline commit (e.g. `954f07f` for the starter). If it
is empty, ask which commit to compare against; do not guess.

1. **HEAD must be clean and green.** If `git status --short` shows changes to
   `src/` or `tests/`, stop and say so: the comparison would not match any
   commit. Run `make all && make test` in the repo. If a test fails, stop
   and report it; do not compare scores from a red pipeline.

2. **Baseline in a worktree.** Resolve the commit with
   `git rev-parse --short $ARGUMENTS`, then
   `git worktree add /tmp/run-pipeline-<sha> <sha>` (reuse it if it already
   exists). Run `make all` inside it. Never check the baseline out in the main
   repo, and never delete with `rm -rf` (denied); clean up with
   `git worktree remove /tmp/run-pipeline-<sha>`.

3. **Delta.** Run
   `python .claude/skills/run-pipeline/delta.py /tmp/run-pipeline-<sha>/reports/metrics.json reports/metrics.json`
   and paste its table verbatim. It reads validation numbers only.

4. **Report** the table, the row-count change (a longer lag window costs
   training rows), and one sentence per model on the direction of the
   change. Always include both baselines. A model below persistence, or a
   negative R^2, is a finding: state it, don't explain it away.

Do not open the test-set numbers in `reports/metrics.json` during this
skill. Test is read once, after all feature and model work, for REPORT.md.
