# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-26: Ex 1 feature `cnt_roll_14` (mean of the 14 days before d; LAG_WARMUP 7 -> 14). Fixed `cnt_lag_7 = shift(LAG_WARMUP)`, which the warm-up change had silently made a 14-day lag, to `shift(7)`, with a calendar-walk test. Validation R^2 without -> with `cnt_roll_14`: ridge 0.6475 -> 0.6919, hgb 0.2185 -> 0.1643; n_train 348 -> 334.
- 2026-11-26: KEEP `cnt_roll_14` under the /new-feature 0.01 rule (drop if validation R^2 gains < 0.01): ridge passes (+0.0444), hgb drops (-0.0542); the hgb drop is reported as a finding, not a reason to drop.
- 2026-11-26: Classify every raw column in `src/config.py`, in three allowed sets alongside the three FORBIDDEN ones: PASSTHROUGH (temp, atemp, hum, windspeed), ENCODED (dteday, holiday, workday, weather), REDUNDANT (season, mnth, weekday). Contract test fails on any unclassified or doubly classified column, so a new raw column cannot reach the model unreviewed.
- 2026-11-26: Seeded fault 3 (`encode_weather` raise removed) stayed green, so the guard was untested. Restoring the raise was not enough: added `test_unknown_weather_label_raises` and `test_relabelled_weather_fails_the_build`, both red against the fault.
- 2026-11-26: Seeded fault 4 (Bash write into `data/raw/`): both, hook chosen by author. A PreToolUse Bash hook (`.claude/hooks/protect_raw.sh`, tested in `tests/test_hooks.py`) blocks `cp`/`mv`/`tee`/redirect writes into `data/raw/` before they run; `RAW_SHA256` + `test_raw_csv_is_unmodified` stays as the backstop for routes the hook's patterns miss (variables, `python -c`, scripts).
- 2026-11-26: Leave `test_rolling_mean_excludes_today` as is (one row, inside a skip-if-gap `if`). It caught seeded fault 2; the weakness is noted in docs/SEEDED_FAULTS.md.
- 2026-11-26: `agent/audit.py` (claude-opus-5-5) flagged same-day weather (temp, atemp, hum, windspeed, weather_severity) as a predictor of same-day `cnt`. Not leakage, but the scores are a nowcast (weather assumed known), not day-ahead forecast accuracy. Kept as is; REPORT.md states the caveat.
- 2026-11-26: Ex 3 peer audit of Gavin's repo @ 6da9aee: PASS, with one fix requested (`cnt_lag_3` still built despite RECOMMEND DROP), plus the latent `cnt_lag_7 = shift(LAG_WARMUP)` trap the auditor missed. Verdict paragraph in docs/AUDIT.md is the author's judgment.
- 2026-11-26: Ex 4 (target transforms, chosen on validation only): stay with ridge, untransformed. Best transform was hgb/ratio (cnt / cnt_roll_7), valid R^2 0.7118 / MAE 741.9 vs ridge 0.6919 / 763.2 (+0.0199 R^2); not adopted. Reason: the +0.02 R^2 edge is small, comes from a single validation split, and doesn't justify a less interpretable model. Other valid R^2: ridge/diff 0.6915, hgb/diff 0.6161, ridge/ratio 0.4966, hgb/log 0.0789, ridge/log -0.1653.
- 2026-11-26: Ex 5, no specific use case: deploy ridge over persistence. Ridge wins validation (R^2 0.6919 vs 0.4507, MAE 763.2 vs 900.6) and test R^2 (0.6268 vs 0.5099) with fewer test misses over 2000 rides (10 vs 17); caveat: persistence wins test MAE (840.1 vs 870.9) and median error (506.5 vs 765.9), and ridge under-predicts H2 2012 by ~395 rides/day.
