# Recession Monitor Validation Report

**Ruleset:** `0.1.0-provisional`  
**Validation type:** Current-vintage pseudo-real-time backtest  
**Coverage:** 1967-04-30 through 2026-09-30 (714 months)
**Fully observed prediction window:** through 2025-09-30 (702 months)

## Summary metrics

Orange-or-Red is treated as the positive classification. The target is an active recession or a recession start within the configured forecast horizon.

| Metric | Result |
|---|---:|
| Precision | 57.4% |
| Recall | 58.3% |
| Specificity | 85.1% |
| False-positive state transitions | 8 |

## Recession episodes

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

## False-positive transition dates

1986-04-30, 1986-06-30, 1993-03-31, 1995-11-30, 2010-08-31, 2011-05-31, 2021-02-28, 2024-03-31

## State occupancy

| State | Months |
|---|---:|
| GREEN | 418 |
| ORANGE | 108 |
| RED | 79 |
| YELLOW | 109 |

## Material caveats

- Historical values are the latest revised FRED observations, not the values known on each historical date.
- Observation dates are used as monthly anchors; exact historical release lags are not reconstructed.
- Episode timing is reported as positive for months of lead and negative for months of lag after the NBER start month.
- The high-yield OAS feed has limited redistributed history and is therefore supplemented by BAA10Y for long-history credit validation.
- Thresholds were frozen before this run and were not tuned to improve these results.
- A decision-grade validation requires ALFRED vintages or prospectively stored source snapshots.

## Readiness

**Needs further validation before decision use.** The engine is deterministic and reproducible from its retained inputs, but the historical test is not yet vintage-correct.
