"""Exercise 4: can a target transformation let the booster compete?

The trees fail because 2012 demand is ~65% above anything in 2011, and a
tree cannot predict outside the range of targets it was trained on. Each
transform below re-expresses cnt as something whose 2012 range looks like
2011's, fits on that, and maps predictions back to rides before scoring.
Every score is on the original scale, so it is comparable with
reports/metrics.json.

  none   cnt                          (the untransformed models)
  log    log1p(cnt)                   level growth becomes a shift
  diff   cnt - cnt_lag_1              change from yesterday
  ratio  cnt / cnt_roll_7             level relative to the past week

Selection is on validation only. `--test NAME` scores one chosen transform
on test, once, after the choice is recorded in docs/DECISIONS.md.

Run: python -m src.transform            (validation only)
     python -m src.transform --test NAME
"""
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import PROCESSED, TARGET, TRANSFORM_METRICS
from src.features import feature_columns
from src.train import MODELS, temporal_split

# name -> (forward: (y, X) -> z, inverse: (z_hat, X) -> y_hat)
TRANSFORMS = {
    "none": (lambda y, X: y, lambda z, X: z),
    "log": (lambda y, X: np.log1p(y), lambda z, X: np.expm1(z)),
    "diff": (lambda y, X: y - X["cnt_lag_1"], lambda z, X: z + X["cnt_lag_1"]),
    "ratio": (lambda y, X: y / X["cnt_roll_7"], lambda z, X: z * X["cnt_roll_7"]),
}
TRANSFORMED_MODELS = ["ridge", "hgb"]


def score(model_name: str, transform: str, train, part, cols) -> dict:
    forward, inverse = TRANSFORMS[transform]
    model = clone(MODELS[model_name])
    model.fit(train[cols], forward(train[TARGET], train[cols]))
    pred = inverse(pd.Series(model.predict(part[cols]), index=part.index), part[cols])
    return {
        "r2": round(float(r2_score(part[TARGET], pred)), 4),
        "mae": round(float(mean_absolute_error(part[TARGET], pred)), 1),
    }


def run(test_transform: str | None = None) -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {"valid": {}}
    for transform in TRANSFORMS:
        for name in TRANSFORMED_MODELS:
            results["valid"][f"{name}/{transform}"] = score(name, transform, train, valid, cols)

    if test_transform is not None:
        # The bar (untransformed ridge) and both baselines, scored on the
        # same test rows as the chosen transform.
        results["test"] = {
            f"{name}/{t}": score(name, t, train, test, cols)
            for t in sorted({"none", test_transform})
            for name in TRANSFORMED_MODELS
        }
        for name in ("baseline_mean", "baseline_persistence"):
            results["test"][name] = score(name, "none", train, test, cols)
        results["test_transform"] = test_transform
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", choices=[t for t in TRANSFORMS if t != "none"])
    args = ap.parse_args()

    res = run(args.test)
    TRANSFORM_METRICS.parent.mkdir(parents=True, exist_ok=True)
    TRANSFORM_METRICS.write_text(json.dumps(res, indent=2))
    best = max(res["valid"], key=lambda k: res["valid"][k]["r2"])
    print(
        f"OK transform: {len(res['valid'])} model/transform pairs on validation; "
        f"best {best} R^2 {res['valid'][best]['r2']}"
        + (f"; test scored for {args.test}" if args.test else "")
        + f" -> {TRANSFORM_METRICS.name}"
    )
