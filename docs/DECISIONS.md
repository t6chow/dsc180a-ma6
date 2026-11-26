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
- 2026-11-26: Seeded fault 4 (Bash write into `data/raw/`): pin the raw CSV with `RAW_SHA256` and `test_raw_csv_is_unmodified` rather than a PreToolUse Bash hook, because it catches a change by any route, not just the commands a hook pattern recognises.
- 2026-11-26: Leave `test_rolling_mean_excludes_today` as is (one row, inside a skip-if-gap `if`). It caught seeded fault 2; the weakness is noted in docs/SEEDED_FAULTS.md.
- 2026-11-26: `agent/audit.py` (claude-opus-5-5) flagged same-day weather (temp, atemp, hum, windspeed, weather_severity) as a predictor of same-day `cnt`. Not leakage, but the scores are a nowcast (weather assumed known), not day-ahead forecast accuracy. Kept as is; REPORT.md states the caveat.
