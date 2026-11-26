"""Exercise 5: does ridge beat persistence, and on which days?

R^2 and MAE disagree on test (ridge wins R^2, persistence wins MAE), so
this breaks the errors down: typical-day error (median), share of days
each model is closer, large misses, bias, and MAE without Hurricane Sandy
and the day after it. Reporting only; nothing here selects a model.

Run: python -m src.compare
"""
import json

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import mean_absolute_error, r2_score

from src.config import COMPARE_METRICS, PROCESSED, STORM_DAYS, TARGET
from src.features import feature_columns
from src.train import MODELS, temporal_split

BIG_MISS = 2000  # rides; roughly a third of a typical 2012 day


def error_profile(y: np.ndarray, pred: np.ndarray) -> dict:
    err = np.abs(y - pred)
    return {
        "r2": round(float(r2_score(y, pred)), 4),
        "mae": round(float(mean_absolute_error(y, pred)), 1),
        "median_ae": round(float(np.median(err)), 1),
        "n_big_miss": int((err > BIG_MISS).sum()),
        "max_err": round(float(err.max()), 0),
        "mean_signed_err": round(float((pred - y).mean()), 1),
    }


def run() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    ridge = clone(MODELS["ridge"]).fit(train[cols], train[TARGET])
    persistence = clone(MODELS["baseline_persistence"]).fit(train[cols])

    results = {"big_miss_threshold": BIG_MISS}
    for split, part in [("valid", valid), ("test", test)]:
        y = part[TARGET].to_numpy(dtype=float)
        preds = {"ridge": ridge.predict(part[cols]), "persistence": persistence.predict(part[cols])}
        out = {name: error_profile(y, p) for name, p in preds.items()}
        out["n_days"] = len(y)
        out["share_ridge_closer"] = round(
            float(np.mean(np.abs(y - preds["ridge"]) < np.abs(y - preds["persistence"]))), 3
        )
        storm = part.dteday.isin(pd.to_datetime(STORM_DAYS)).to_numpy()
        if storm.any():
            out["mae_excl_storm"] = {
                name: round(float(mean_absolute_error(y[~storm], p[~storm])), 1)
                for name, p in preds.items()
            }
        results[split] = out
    return results


if __name__ == "__main__":
    res = run()
    COMPARE_METRICS.parent.mkdir(parents=True, exist_ok=True)
    COMPARE_METRICS.write_text(json.dumps(res, indent=2))
    t = res["test"]
    print(
        f"OK compare: test MAE ridge {t['ridge']['mae']} vs persistence {t['persistence']['mae']}; "
        f"ridge closer on {t['share_ridge_closer']:.1%} of {t['n_days']} days -> {COMPARE_METRICS.name}"
    )
