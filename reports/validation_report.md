# Recession Monitor Validation Report

**Ruleset:** `0.1.1-provisional`  
**Validation type:** Current-vintage pseudo-real-time backtest  
**Coverage:** 1967-04-30 through 2026-09-30 (714 months)
**Fully observed monthly prediction window:** through 2025-09-30 (702 months)

## What is being measured

This report deliberately separates three tests that have different units and denominators. They must not be combined into one hit rate.

| Test | Unit | Question |
|---|---|---|
| Monthly horizon classification | Month | Was the state Orange/Red when recession was active or no more than 12 months away? |
| Recession-event detection | NBER recession | Did any Orange/Red state occur inside the bounded lead/lag window? |
| Alert-episode precision | Consolidated alert episode | Did an observed alert episode overlap or precede a recession? |

## 1. Monthly horizon classification

NBER recession is active or a recession begins within the next 12 months.

| Actual target / Engine state | Orange or Red | Green or Yellow | Total |
|---|---:|---:|---:|
| Target positive | 105 | 75 | 180 |
| Target negative | 54 | 468 | 522 |
| Total | 159 | 543 | 702 |

| Metric | Result | Denominator |
|---|---:|---:|
| Monthly precision | 66.0% | 159 Orange/Red months |
| Monthly recall | 58.3% | 180 target-positive months |
| Monthly specificity | 89.7% | 522 target-negative months |

No naive binomial interval is reported because adjacent monthly observations are serially dependent.

## 2. Recession-event detection

**Detected:** 8 of 8 eligible recessions (100.0%).  
**Exact 95% interval:** 63.1% to 100.0%.

Detected when Orange/Red occurs from as early as 18 months before the recession start through 6 months after it; the window cannot cross the previous recession end.

| NBER recession start | First Orange/Red | Lead (+) / lag (-), months | Detected |
|---|---|---:|---|
| 1970-01-31 | 1970-01-31 | 0 | Yes |
| 1973-12-31 | 1974-01-31 | -1 | Yes |
| 1980-02-29 | 1979-04-30 | 10 | Yes |
| 1981-08-31 | 1980-08-31 | 12 | Yes |
| 1990-08-31 | 1989-04-30 | 16 | Yes |
| 2001-04-30 | 2000-08-31 | 8 | Yes |
| 2008-01-31 | 2007-08-31 | 5 | Yes |
| 2020-03-31 | 2019-12-31 | 3 | Yes |

## 3. Consolidated alert episodes

Orange/Red runs separated by 6 or fewer non-alert months are one episode. An observed episode is positive if it overlaps a recession or is followed by a recession start within 18 months.

| Result | Count |
|---|---:|
| True-positive episodes | 7 |
| False-positive episodes | 3 |
| Right-censored episodes | 1 |
| Observed episode precision | 70.0% |
| Exact 95% interval | 34.8% to 93.3% |

| Episode | Start | End | Peak | Alert months | Raw runs merged | Outcome | Context | Matched recession starts |
|---:|---|---|---|---:|---:|---|---|---|
| 1 | 1970-01-31 | 1970-12-31 | RED | 10 | 2 | TRUE_POSITIVE | MATCHED_RECESSION | 1970-01-31 |
| 2 | 1974-01-31 | 1975-05-31 | RED | 15 | 3 | TRUE_POSITIVE | MATCHED_RECESSION | 1973-12-31 |
| 3 | 1979-04-30 | 1982-12-31 | RED | 29 | 5 | TRUE_POSITIVE | MATCHED_RECESSION | 1980-02-29, 1981-08-31 |
| 4 | 1986-04-30 | 1986-06-30 | ORANGE | 2 | 2 | FALSE_POSITIVE | UNMATCHED_STRESS | None |
| 5 | 1989-04-30 | 1991-04-30 | RED | 18 | 3 | TRUE_POSITIVE | MATCHED_RECESSION | 1990-08-31 |
| 6 | 1991-12-31 | 1992-01-31 | ORANGE | 2 | 1 | FALSE_POSITIVE | POST_RECESSION_AFTERSHOCK | None |
| 7 | 2000-08-31 | 2003-09-30 | RED | 37 | 2 | TRUE_POSITIVE | MATCHED_RECESSION | 2001-04-30 |
| 8 | 2007-08-31 | 2010-09-30 | RED | 34 | 4 | TRUE_POSITIVE | MATCHED_RECESSION | 2008-01-31 |
| 9 | 2019-12-31 | 2021-02-28 | RED | 10 | 3 | TRUE_POSITIVE | MATCHED_RECESSION | 2020-03-31 |
| 10 | 2024-03-31 | 2024-03-31 | ORANGE | 1 | 1 | FALSE_POSITIVE | UNMATCHED_STRESS | None |
| 11 | 2025-06-30 | 2026-01-31 | ORANGE | 5 | 2 | RIGHT_CENSORED | OUTCOME_NOT_YET_OBSERVABLE | None |

## Transition diagnostics

There were 28 raw entries into Orange/Red. Transitions are state-machine diagnostics, not independent forecast events.

1970-01-31, 1970-09-30, 1974-01-31, 1974-06-30, 1974-08-31, 1979-04-30, 1979-08-31, 1980-02-29, 1981-02-28, 1981-09-30, 1986-04-30, 1986-06-30, 1989-04-30, 1989-07-31, 1990-08-31, 1991-12-31, 2000-08-31, 2000-10-31, 2007-08-31, 2007-12-31, 2010-05-31, 2010-08-31, 2019-12-31, 2020-03-31, 2021-02-28, 2024-03-31, 2025-06-30, 2025-10-31

## State occupancy

| State | Months |
|---|---:|
| GREEN | 441 |
| ORANGE | 91 |
| RED | 72 |
| YELLOW | 110 |

## Material caveats

- Historical values are the latest revised FRED observations, not the values known on each historical date.
- Observation dates are used as monthly anchors; exact historical release lags are not reconstructed.
- Monthly forecast metrics use overlapping 12-month targets and serially dependent observations; their apparent sample size overstates statistical independence.
- Event detection and alert-episode precision are separate tests with different denominators and must not be combined into a hit rate.
- Clopper-Pearson intervals quantify small-sample binomial uncertainty but do not remove dependence among business cycles.
- The high-yield OAS feed has limited redistributed history and is therefore supplemented by BAA10Y for long-history credit validation.
- Commercial real-estate delinquency is a lagging quarterly corroborator and cannot set or upgrade the credit state in this ruleset.
- Ruleset 0.1.1 changes only the CRE role and validation definitions; thresholds were not optimized against the revised results.
- A decision-grade validation requires ALFRED vintages or a sufficiently long prospectively frozen source archive.

## Readiness

**Share with caveats; not ready for portfolio decision use.** The engine is deterministic and reproducible from retained inputs, and the three validation questions are now explicit. Historical revision leakage remains unresolved.
