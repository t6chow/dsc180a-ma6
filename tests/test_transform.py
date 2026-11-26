"""Exercise 4 harness checks: transforms invert exactly, and the untransformed
rows agree with reports/metrics.json, so the comparison is like for like."""
import json

import pytest

from src.config import METRICS, TARGET
from src.features import build_features, feature_columns
from src.ingest import load_raw
from src.transform import TRANSFORMS, TRANSFORMED_MODELS, run


@pytest.fixture(scope="module")
def feats():
    return build_features(load_raw())


@pytest.mark.parametrize("name", list(TRANSFORMS))
def test_transform_round_trips(feats, name):
    forward, inverse = TRANSFORMS[name]
    X, y = feats[feature_columns(feats)], feats[TARGET]
    assert inverse(forward(y, X), X).to_numpy() == pytest.approx(y.to_numpy())


def test_untransformed_rows_match_metrics_json():
    """Requires `make all` first; transform.py must score exactly as train.py."""
    metrics = json.loads(METRICS.read_text())
    valid = run()["valid"]
    for name in TRANSFORMED_MODELS:
        assert valid[f"{name}/none"] == metrics[name]["valid"]
