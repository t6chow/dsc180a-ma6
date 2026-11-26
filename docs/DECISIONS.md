# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-26: Ex 1 feature `cnt_roll_14` (mean of the 14 days before d; LAG_WARMUP 7 -> 14). Fixed `cnt_lag_7 = shift(LAG_WARMUP)`, which the warm-up change had silently made a 14-day lag, to `shift(7)`, with a calendar-walk test. Validation R^2 without -> with `cnt_roll_14`: ridge 0.6475 -> 0.6919, hgb 0.2185 -> 0.1643; n_train 348 -> 334.
