# Forecasting daily Capital Bikeshare demand: methodology report

Daily ride counts (`cnt`), 2011-01-03 to 2012-12-31 (728 rows; the mirror is
missing 2011-03-10). Train = 2011, validation = H1 2012, test = H2 2012, split
by date. Every number below is copied from a committed file named next to it.
From a clean clone (checked at f418cfe), `make all` regenerates
`reports/metrics.json` byte-identically, as do `make compare` for
`reports/compare.json` and `python -m src.transform --test ratio` for
`reports/transform.json`. Plain `make transform` writes the validation section only.

## Results

Four models before and after the Exercise 1 feature (`cnt_roll_14`, the mean of
the 14 days before *d*). "Starter" is a real `make all` run of the unmodified
starter (954f07f, via `/run-pipeline 954f07f`). "HEAD" is `reports/metrics.json`.
n_valid = 182 and n_test = 184 in both; n_train falls from 348 to 334 because the
14-day window needs 14 days of history before the first row and after the
2011-03-10 gap.

| Model | Features | n_train | Valid R^2 | Valid MAE | Test R^2 | Test MAE |
|---|---|---|---|---|---|---|
| Mean baseline | starter (954f07f) | 348 | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| Mean baseline | + cnt_roll_14 (HEAD) | 334 | -0.8583 | 1965.6 | -2.0333 | 2793.1 |
| Persistence baseline | starter (954f07f) | 348 | 0.4507 | 900.6 | 0.5099 | 840.1 |
| Persistence baseline | + cnt_roll_14 (HEAD) | 334 | 0.4507 | 900.6 | 0.5099 | 840.1 |
| Ridge | starter (954f07f) | 348 | 0.6475 | 832.9 | 0.5833 | 947.1 |
| Ridge | + cnt_roll_14 (HEAD) | 334 | 0.6919 | 763.2 | 0.6268 | 870.9 |
| HGB | starter (954f07f) | 348 | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| HGB | + cnt_roll_14 (HEAD) | 334 | 0.1643 | 1341.2 | -0.6534 | 2087.9 |

`cnt_roll_14` was kept under the `/new-feature` rule (drop if validation R^2
gains less than 0.01): ridge gains +0.0444, HGB loses 0.0542. The HGB drop is
reported, not used as a reason to drop. Persistence is unchanged because it only
uses `cnt_lag_1` and the validation and test rows are the same.

Three caveats about what these numbers mean:

- **Nowcast, not forecast.** Temperature, humidity, wind and weather severity
  are the same day's observations. No column leaks the target, but the scores
  assume that day's weather is known, so they overstate day-ahead accuracy
  (flagged by `agent/audit.py`, `reports/audit.jsonl`).
- **The persistence gap grew.** The starter's DECISIONS.md says persistence
  "is within 0.07 R^2 of ridge". That was true at the starter (0.5099 vs 0.5833
  on test). With `cnt_roll_14` the gap is 0.1169. Starter lines in DECISIONS.md
  are not edited, so the correction is here.
- **A bug was fixed on the way.** The commit that added `cnt_roll_14` (8b18548)
  raised `LAG_WARMUP` from 7 to 14. `cnt_lag_7` was written as
  `shift(LAG_WARMUP)`, so it silently became a 14-day lag with every test green.
  d52e32b made it `shift(7)` and added a calendar-walk test over 686 of 700 rows.
  The table is from the fixed code.

Test numbers were read for this table after all feature and model choices were
recorded in `docs/DECISIONS.md`. The selection decisions (Exercise 1 keep/drop,
Exercise 4 transform) cite validation numbers only. The Exercise 5 deployment
judgment, made after all selection, uses test.

## Headline finding

**The gradient-boosted trees fail because demand grew, not because the features
are weak.** Mean daily rides went from 3427.3 in 2011 to 5599.9 in 2012 (+63.4%;
`load_raw().groupby(dteday.dt.year).cnt.mean()`). A tree predicts by averaging
training targets in a leaf, so a model trained on 2011 cannot predict counts
far above the 2011 range. HGB's test R^2 is -0.6534, worse than persistence
(0.5099) and above only the mean baseline (-2.0333). Adding a better lag feature
made it worse (valid R^2 0.2185 -> 0.1643). A likely reason, not tested: the
lags carry 2012's higher level into input ranges with no 2011 examples.

Exercise 4 confirms the diagnosis. Asking HGB to predict `cnt / cnt_roll_7`
(today relative to last week, a quantity whose range does not grow) moves its
test R^2 from -0.6534 to 0.5962 with the same features. Ridge extrapolates
linearly, so it degrades instead of failing: it under-predicts H2 2012 by 394.6
rides a day on average (`reports/compare.json`).

## Exercise 4: target transformation

Three transforms of `cnt`, each fit on 2011 and mapped back to rides before
scoring (`src/transform.py`, `make transform`, `reports/transform.json`):
`log` = log1p(cnt), `diff` = cnt - cnt_lag_1, `ratio` = cnt / cnt_roll_7. Both
inputs to `diff` and `ratio` are known before day *d*. `tests/test_transform.py`
checks each inverse undoes its forward exactly, and that the untransformed rows
equal `reports/metrics.json`. The rule for a defensible transform was: chosen on
validation only, and it must beat untransformed ridge (a tie is not enough).

| Model / transform | Valid R^2 | Valid MAE |
|---|---|---|
| ridge / none (the bar) | 0.6919 | 763.2 |
| hgb / none | 0.1643 | 1341.2 |
| ridge / log | -0.1653 | 1345.0 |
| hgb / log | 0.0789 | 1423.1 |
| ridge / diff | 0.6915 | 763.0 |
| hgb / diff | 0.6161 | 823.5 |
| ridge / ratio | 0.4966 | 987.7 |
| hgb / ratio | 0.7118 | 741.9 |

On validation, `hgb / ratio` beats the bar by +0.0199 R^2 and 21.3 MAE, so it
meets the rule. The decision was still to **stay with untransformed ridge**:
the +0.02 R^2 edge is small, comes from a single validation split, and doesn't
justify a less interpretable model. That decision was recorded (c87ebe3) before
any transform was scored on test. Then `hgb / ratio` was scored on test once,
as a finding (a3b05a3):

| Model / transform | Test R^2 | Test MAE |
|---|---|---|
| ridge / none | 0.6268 | 870.9 |
| hgb / none | -0.6534 | 2087.9 |
| hgb / ratio | 0.5962 | 879.4 |
| ridge / ratio | 0.1682 | 1370.4 |
| persistence | 0.5099 | 840.1 |

The validation edge did not survive: on test, `hgb / ratio` is 0.0306 R^2 behind
ridge. The transform does let HGB compete, taking it from the worst model to
0.0306 R^2 behind the best. It does not let HGB win. `log` gives ridge a
negative validation R^2 (-0.1653); we did not investigate why.

## Exercise 5: ridge vs persistence

Ridge beats persistence on validation by a wide margin (R^2 0.6919 vs 0.4507,
MAE 763.2 vs 900.6). On test the metrics disagree: ridge wins R^2 (0.6268 vs
0.5099) but loses MAE (870.9 vs 840.1). `src/compare.py` (`make compare`,
`reports/compare.json`) shows why:
- **Persistence wins the typical test day.** Its median absolute error is 506.5
  against ridge's 765.9, and ridge is closer on only 44.0% of the 184 days.
- **Ridge wins on large misses.** It misses by more than 2000 rides on 10 days,
  persistence on 17. Squared error weights those misses heavily, which is why
  ridge wins R^2.
- **Ridge's typical-day loss is mostly bias.** Ridge under-predicts by 394.6
  rides a day (persistence: +16.1), the Headline finding's level problem in
  milder form.
- **It is not Hurricane Sandy.** Without 2012-10-29 and the day after (when
  persistence predicts 22 rides), MAE is still 844.5 for ridge and 819.0 for
  persistence.

So ridge does not beat persistence outright. It beats it on R^2, on validation
and on bad days, and loses on ordinary days. With no specific use case, weighing
R^2 and MAE together, the decision is to **deploy ridge**. Ridge tracks the
large swings (R^2 0.63 vs 0.51, 10 vs 17 misses over 2,000 rides), which matter
more for staffing and rebalancing than a 31-ride gap in typical error. The cost
is accepted, not hidden: persistence is 30.8 rides better on test MAE, costs
nothing to run, and has no bias. Ridge's bias of -394.6 rides a day is the known
cost; a target relative to recent demand, as in Exercise 4, is one way to
address it.

## Attribution

Model: qwen3.5:9b via Ollama (64k context) wrote the Exercise 1 failing test; switched to Claude Opus 5.5 (hosted) for the rest.

**Agent-generated** (Claude Opus 5.5 unless noted; every commit passes
`make test` except the deliberately red ones in Exercise 1 and the seeded faults):

- `tests/test_leakage.py::test_rolling_14_excludes_today` (qwen3.5:9b, b8d5b73).
- `src/features.py`: `cnt_roll_14` (8b18548); the `cnt_lag_7 = shift(7)` fix,
  comment fix and `tests/test_leakage.py::test_lag_7_is_a_true_7_day_calendar_lag`
  (d52e32b).
- `src/config.py`: `PASSTHROUGH_COLS`, `ENCODED_COLS`, `REDUNDANT_COLS`,
  `CLASSIFIED` (aca1320); `RAW_SHA256` (c758fd6); `TRANSFORM_METRICS`,
  `COMPARE_METRICS`, `STORM_DAYS`.
- `tests/test_contract.py`: `test_every_raw_column_is_classified` (f1c9608),
  `test_unknown_weather_label_raises`, `test_relabelled_weather_fails_the_build`
  (bcc755c), `test_raw_csv_is_unmodified` (c758fd6).
- `.claude/hooks/protect_raw.sh` (PreToolUse Bash hook), its `settings.json`
  registration, and `tests/test_hooks.py`.
- `src/transform.py`, `tests/test_transform.py`, `src/compare.py`, the
  `transform` and `compare` Makefile targets.
- `.claude/skills/run-pipeline/` (`SKILL.md`, `delta.py`).
- Documents: `docs/SEEDED_FAULTS.md` (all pasted output is from real runs),
  `docs/AUDIT.md` except the verdict, the wording of the 2026-11-26 lines in
  `docs/DECISIONS.md`, CLAUDE.md additions, this report's prose.
- Agent decisions (dated 2026-11-26 lines in `docs/DECISIONS.md`):

  | Decision | DECISIONS.md line begins |
  |---|---|
  | Classify every raw column in three allowed sets | "Classify every raw column" |
  | Fault 3: test the weather guard, not just restore it | "Seeded fault 3" |
  | Leave `test_rolling_mean_excludes_today` as is | "Leave `test_rolling_mean_excludes_today`" |
- Reviewers: the `leakage-auditor` subagent audited d52e32b (PASS) and Gavin's
  repo (`docs/AUDIT.md`). `agent/audit.py` with `claude-opus-5-5` audited this
  repo (`reports/audit.jsonl`).

**Author's decisions**, each a dated 2026-11-26 line in `docs/DECISIONS.md`:

| Decision | DECISIONS.md line begins |
|---|---|
| Ex 1 feature `cnt_roll_14`, and the `cnt_lag_7` fix | "Ex 1 feature `cnt_roll_14`" |
| Keep `cnt_roll_14` despite the HGB drop | "KEEP `cnt_roll_14`" |
| Fault 4: SHA-256 pin first (c758fd6), PreToolUse Bash hook added later (a36feab); both stay | "Seeded fault 4" |
| Keep same-day weather; report as a nowcast | "`agent/audit.py` (claude-opus-5-5) flagged" |
| Ex 3 verdict on Gavin's repo | "Ex 3 peer audit" |
| Ex 4: stay with untransformed ridge | "Ex 4 (target transforms" |
| Ex 5: deploy ridge | "Ex 5, no specific use case" |
