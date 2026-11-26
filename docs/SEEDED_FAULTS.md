# Seeded faults

Each fault was introduced on purpose with the agent's Edit tool, so the
PostToolUse hook (`.claude/hooks/check_leakage.sh`, which re-runs
`tests/test_leakage.py` after any edit to `src/*.py`) fired exactly as it
would on a real mistake. Each fault and its fix are separate commits. All
output below is pasted from the real runs, not reconstructed.

"Turns to fix" counts agent tool calls from first seeing the red output to
a green `make test`.

## Exercise 1: the failing feature test (b8d5b73)

The `cnt_roll_14` test was committed before the feature existed. Red run at
b8d5b73 (`python -m pytest tests/test_leakage.py -q --tb=line`):

```
.....F..                                                                 [100%]
=================================== FAILURES ===================================
E   AttributeError: 'DataFrame' object has no attribute 'cnt_roll_14'. Did you mean: 'cnt_roll_7'?
/Users/terranchow/Desktop/dsc180a/bikeshare-open/.venv/lib/python3.12/site-packages/pandas/core/generic.py:6194: AttributeError: 'DataFrame' object has no attribute 'cnt_roll_14'. Did you mean: 'cnt_roll_7'?
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_14_excludes_today - AttributeError...
1 failed, 7 passed in 0.23s
```

8b18548 made it pass, and in doing so silently turned `cnt_lag_7` into a
14-day lag that no test covered; d52e32b fixed it and added the test that
would have caught it.

## Fault 1: a forbidden column in `feature_columns`

**Change** (`src/features.py`, `feature_columns`):

```diff
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN - {"registered"}]
```

**Hook stderr**, returned to the agent immediately after the Edit (as
delivered; the harness elided the middle of the `feats` repr):

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /Users/terranchow/Desktop/dsc180a/bikeshare-open/src/features.py:
feats =         dteday  instant  season      yr  ... cnt_lag_1 cnt_lag_7   cnt_roll_7  cnt_roll_14
0   2011-01-17     17.0  WI...286
699 2012-12-31    731.0  WINTER  2012.0  ...    1796.0     920.0  1531.428571  2672.571429

[700 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered'}
E       assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_14', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
======================================= short test summary info ========================================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: forbidden columns in featu...
1 failed, 8 passed in 0.27s
```

**Red test output** (`python -m pytest tests/ -q --tb=line`):

```
......F..........                                                        [100%]
=================================== FAILURES ===================================
E   AssertionError: forbidden columns in feature set: {'registered'}
    assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_14', 'cnt_roll_7', 'dayofweek', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})
/Users/terranchow/Desktop/dsc180a/bikeshare-open/tests/test_leakage.py:31: AssertionError: forbidden columns in feature set: {'registered'}
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 16 passed in 0.99s
```

**Fix:** revert the line. The hook ran silently on the fix Edit (leakage
tests green) and `make test` gave `17 passed in 0.97s`.
**Turns to fix: 2** (one Edit, one `make test`). The assertion message
names the column, so there was nothing to diagnose.

## Fault 2: `.shift(1)` deleted from `cnt_roll_7`

**Change** (`src/features.py`, `build_features`). The rolling mean now
includes today's count, which is the target:

```diff
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(7).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(7).mean()
```

**Hook stderr** (as delivered; the hook's `tail -20` cut it to the end of
the `feats` repr):

```
PostToolUse:Edit hook blocking error from command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh": [${CLAUDE_PROJECT_DIR}/.claude/hooks/check_leakage.sh]: Leakage tests failed after editing /Users/terranchow/Desktop/dsc180a/bikeshare-open/src/features.py:
[700 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.428571428572) == 4240.714285714285 ± 0.00424071
E             
E             comparison failed
E             Obtained: 4389.428571428572
E             Expected: 4240.714285714285 ± 0.00424071

tests/test_leakage.py:73: AssertionError
======================================= short test summary info ========================================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.float64(4389.428571428572)...
1 failed, 8 passed in 0.27s
```

**Red test output** (`python -m pytest tests/ -q --tb=line`):

```
..........F......                                                        [100%]
=================================== FAILURES ===================================
E   assert np.float64(4389.428571428572) == 4240.714285714285 ± 0.00424071
      
      comparison failed
      Obtained: 4389.428571428572
      Expected: 4240.714285714285 ± 0.00424071
/Users/terranchow/Desktop/dsc180a/bikeshare-open/tests/test_leakage.py:73: assert np.float64(4389.428571428572) == 4240.714285714285 ± 0.00424071
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 16 passed in 0.98s
```

Only one test catches this, and it checks a single row (`iloc[200]`) inside an
`if` that would skip the assertion without failing if that row's window had a gap.
