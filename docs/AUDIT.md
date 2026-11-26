# Peer audit: Gavin's bikeshare-open

- **Repo:** https://github.com/GavinWu555/bikeshare-open
- **Audited commit:** `6da9aee` ("Add contract test ensuring all raw CSV columns are classified")
- **Diff audited:** `git diff 47120f6 6da9aee` (his unmodified starter to HEAD, 8 commits)
- **Auditor:** the `leakage-auditor` subagent (`.claude/agents/leakage-auditor.md`), run from Claude Code
  on Claude Opus 5.5, 2026-11-26. It had read-only access to the clone and ran his test suite; nothing
  in his repo was modified.

## Auditor output (verbatim)

> The harness prefixed the report with one line, which is not part of the auditor's output and is
> omitted here: a note that the text matched a `settings-json` pattern (it mentions
> `.claude/settings.json` in a factual context) and that control tags were neutralised. No tags were present.

**Verdict: PASS.** Nothing blocks. All five methodology checks pass on Gavin's diff (47120f6..6da9aee). There are three non-blocking problems: one decision is left unresolved and two doc claims are wrong.

**How I checked.** I read the code and ran his suite (17 passed; the working tree is still clean). I rebuilt every metric in memory, with and without `cnt_lag_3`. I also ran his tests against deliberately broken copies of the features and raw data, in memory only, to see whether they can fail. Nothing in his repo was modified. My scratch scripts are in /tmp/audit_gavin/. His raw CSV has the same SHA-256 as ours (a6bed157…), so the Fault 4 `cp` left nothing behind.

**The five checks**
1. **Target leakage: pass.** `src/features.py:75` is `out[TARGET].shift(3)`. The final feature list is temp, atemp, hum, windspeed, dayofweek, is_weekend, is_holiday, is_workday, month_sin, month_cos, weather_severity, cnt_lag_1, cnt_lag_3, cnt_lag_7, cnt_roll_7. None of these is casual, registered or cnt, or a sum of them.
2. **Temporal ordering: pass.** The split is by date: 348 train / 182 valid / 184 test. The scaler is inside the ridge pipeline and is fit on train only. DECISIONS.md:11 reports validation numbers only, so there is no tuning on test.
3. **Calendar gaps: pass.** The lag is computed after `reindex_to_calendar` and stays within `LAG_WARMUP=7`. The new test (`tests/test_leakage.py:50-59`) compares against calendar dates and requires more than 600 rows checked. It fails if lag_3 is replaced by lag_1 or by `cnt`. A row-based (non-calendar) shift3 would pass it, but I checked: the rows that version gets wrong after the 2011-03-10 gap are already dropped by `cnt_roll_7`, so no number changes.
4. **Silent row loss: pass.** There are still 714 rows, which hits the `test_contract.py:28-43` limit of 14 lost rows exactly. With the weather guard removed and one label changed to "SNOW", that test fails ("lost 15 rows; expected at most 14").
5. **Baselines: pass.** Both are in `MODELS` and scored on every split. At HEAD, test R²: mean -2.144, persistence 0.510, ridge 0.581, hgb -0.565.

**Non-blocking findings, most important first**

1. **`docs/DECISIONS.md:11` says "RECOMMEND DROP", but `src/features.py:75` still builds `cnt_lag_3`, so HEAD ships the feature.** His numbers reproduce exactly: ridge valid R² 0.6475 → 0.6462, MAE 832.9 → 835.2; hgb 0.2185 → 0.1891, MAE 1296.6 → 1318.2. Leaving it in changes every metric HEAD produces. Ridge test R² goes 0.5833 → 0.5813 and hgb test R² goes -0.4975 → -0.5653. It also makes `DECISIONS.md:6` ("honest ridge 0.583") out of date at HEAD, where it is 0.581. Fix: either delete `features.py:75` (the lag_3 tests can stay as a record or be removed), or add a line saying it is kept on purpose and update line 6.

2. **`docs/SEEDED_FAULTS.md:265-267` overstates the Fault 3 risk.** It says that with the weather guard removed, "the whole dataset disappears with no error" and that the guard is "the only thing standing between a data swap and a silently empty training set". That is false: the row-loss test in `tests/test_contract.py:28-43` catches the result, and I confirmed it fails with a single unseen label. What is true is that no test calls `encode_weather` directly or uses `pytest.raises` (confirmed by grep), and his write-up proposed that test but never added it. Fix: correct the claim, or add the proposed `test_unmapped_weather_label_raises`.

3. **The new contract test claims more than it checks.** Two parts:
   - The docstring at `tests/test_contract.py:61-63` says "a new column cannot enter the modelling table silently". That holds only for raw CSV columns. I confirmed it fails on a new raw column, but a column created in `build_features` still gets in automatically through `select_dtypes`.
   - `RAW_FEATURE_COLS` (`src/config.py:48-59`) is a hand-typed list that `feature_columns()` never reads. Six of its entries (season, mnth, holiday, weekday, workday, weather) are strings that never reach the model, so the name suggests a feature set that isn't the real one.

   Fix: narrow the docstring to raw columns, and rename the set to something like `RAW_ALLOWED_COLS`.

A fourth point is starter code outside the diff, so I've left it out of the findings. `tests/test_leakage.py:71` (`if all(...)`) could skip its assertion without saying so. It does run on the current data: iloc[200] is 2011-08-06, and Fault 2 shows it firing.

**docs/SEEDED_FAULTS.md looks real and matches the code:**
- **Exercise 1:** `........FF......` with 16 tests, the failures at positions 9-10, and "2 failed, 14 passed" match the tests at 510f880. The 28 → 29 column counts are right. The shortened DataFrame output matches real values, e.g. row 0 lag_1 822 / lag_3 1510 and row 712 lag_7 1787 / roll_7 1530.142857.
- **Faults 1 and 2:** the hook output is exactly 20 lines, which is what `tail -20` in `check_leakage.sh` produces. "1 failed, 8 passed" is right for the 9 leakage tests. I reproduced Fault 2's numbers myself: on 2011-08-06, 4389.0 includes today's count and 4414.857 is the correct prior-7-day mean.
- **Fault 3:** "16 passed" and "ridge 0.6462 / hgb 0.1891" are right. The weather labels really are BAD 20 / GOOD 463 / MISTY 245 with no NaN, and the `src/config.py:16` line reference is right.
- **Fault 4:** "total 184" fits the file sizes (86325 B + 19 B on 4 KB blocks), and its claim that the hook only fires on Edit/Write matches `.claude/settings.json`. Small gap: `git status` is listed as a command but its output isn't shown.

## Verdict

**PASS, with one fix requested.** The methodology holds: no target leakage, a date-based split with
no tuning on test, both baselines reported, and the seeded-fault output is real (the auditor
reproduced the numbers to the digit). The fix: DECISIONS.md:11 recommends dropping `cnt_lag_3`, but
`features.py:75` still builds it, so every metric at HEAD includes a feature the repo's own analysis
rejected (ridge valid R^2 0.6462 instead of 0.6475). Gavin should delete the line or record that it
was kept on purpose. Two lesser points: SEEDED_FAULTS.md overstates Fault 3 (the row-loss test does
catch an unseen label), and the contract test's docstring claims more than raw columns. One thing
the auditor missed, because it is starter code outside the diff: `features.py:76` builds `cnt_lag_7`
as `shift(LAG_WARMUP)`. It is correct at `LAG_WARMUP = 7`, but it is the exact bug that turned our
`cnt_lag_7` into a 14-day lag when we raised the warm-up for `cnt_roll_14`, and no test in the repo
checks lag_7.
