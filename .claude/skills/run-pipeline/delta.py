"""Validation-only delta between two reports/metrics.json files.

Usage: python .claude/skills/run-pipeline/delta.py BASE.json HEAD.json

Prints a markdown table of validation R^2 and MAE for every model in both
files. Test-set numbers are never read: comparing on test while iterating
is tuning on test.
"""
import json
import sys

MODELS = ["baseline_mean", "baseline_persistence", "ridge", "hgb"]


def main(base_path: str, head_path: str) -> None:
    base = json.load(open(base_path))
    head = json.load(open(head_path))

    print("| model | valid R^2 base | valid R^2 head | delta | valid MAE base | valid MAE head | delta |")
    print("|---|---|---|---|---|---|---|")
    for name in MODELS:
        if name not in base or name not in head:
            print(f"| {name} | {'missing' if name not in base else ''} | {'missing' if name not in head else ''} | | | | |")
            continue
        b, h = base[name]["valid"], head[name]["valid"]
        print(
            f"| {name} | {b['r2']:.4f} | {h['r2']:.4f} | {h['r2'] - b['r2']:+.4f} "
            f"| {b['mae']:.1f} | {h['mae']:.1f} | {h['mae'] - b['mae']:+.1f} |"
        )

    print()
    for key in ["n_train", "n_valid", "n_features"]:
        print(f"{key}: {base[key]} -> {head[key]}")
    added = sorted(set(head["features"]) - set(base["features"]))
    removed = sorted(set(base["features"]) - set(head["features"]))
    print(f"features added: {', '.join(added) or 'none'}")
    print(f"features removed: {', '.join(removed) or 'none'}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
