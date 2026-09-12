# Methodology Change Note: 0.1.1-Provisional

## Purpose

This revision resolves two interpretive problems found during review of `0.1.0-provisional`:

1. A quarterly, lagging commercial real-estate delinquency series could create acute credit classifications.
2. Monthly forecast metrics, recession-event detection, and raw state transitions were reported together even though they use different units and denominators.

The archived `0.1.0-provisional` inputs, outputs, and reports remain unchanged under `archive/v0.1.0-provisional/`.

## Rule change

`DRCRELEXFACBS` is now **corroboration-only**. Its reading and threshold flags remain available for interpretation, but it cannot establish credit-layer data availability, elevate the credit state, or upgrade the credit state. Primary credit classification is determined by Baa and high-yield spreads, their 20-trading-day changes, NFCI, and STLFSI.

No numerical signal threshold was optimized or retuned in this revision.

## Validation definitions

The engine now reports three distinct tests:

| Test | Unit | Definition |
|---|---|---|
| Monthly horizon classification | Month | Orange/Red versus a target of active recession or recession beginning within 12 months |
| Recession-event detection | NBER recession episode | Any Orange/Red reading from 18 months before through 6 months after the start, bounded by the preceding recession exit |
| Alert-episode precision | Consolidated Orange/Red episode | Orange/Red runs separated by no more than six quiet months; positive when overlapping or followed by a recession within 18 months |

Raw entries into Orange/Red remain in the output as transition diagnostics. They are not treated as independent forecasts.

## Before-and-after results

Both columns use the same retained, latest-revised FRED payloads. They are not vintage-correct.

| Monthly horizon result | 0.1.0 | 0.1.1 |
|---|---:|---:|
| True-positive months | 105 | 105 |
| False-positive months | 78 | 54 |
| False-negative months | 75 | 75 |
| True-negative months | 444 | 468 |
| Precision | 57.4% | 66.0% |
| Recall | 58.3% | 58.3% |
| Specificity | 85.1% | 89.7% |

Recession-event detection remains 8 of 8. Its two-sided Clopper-Pearson 95% interval is 63.1% to 100.0%, which makes the small-event-count uncertainty explicit.

Under the new six-month cooldown definition, there are seven true-positive alert episodes, three false-positive alert episodes, and one right-censored episode. Observed alert-episode precision is 70.0%, with an exact 95% interval of 34.8% to 93.3%. This wide interval is more informative than a point estimate alone.

## Remaining false-positive episodes

| Start | Context | Layer configuration at entry |
|---|---|---|
| 1986-04 | Unmatched stress | Labor elevated; credit elevated; activity normal |
| 1991-12 | Post-recession aftershock | Labor severe; activity elevated; credit normal |
| 2024-03 | Unmatched stress | Labor elevated; activity elevated; credit normal |

The 2025-06 alert episode is right-censored because its complete 18-month outcome window is not yet observable.

## Interpretation

The apparent improvement in precision is a mechanical consequence of correcting the CRE rule, not evidence that the other thresholds are optimal. Recall is unchanged. The engine remains a deterministic research monitor and is not ready for portfolio decision use.

The next validation gate is point-in-time evidence: ALFRED vintages where practical, supplemented by the prospectively frozen raw-payload archive created by future online runs.
