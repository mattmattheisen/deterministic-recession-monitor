# Deterministic U.S. Recession Monitor

**As of:** 2026-11-19  
**Ruleset:** `0.1.1-provisional`  
**Overall state:** **GREEN**
**Alert required:** **NO** (NO_MATERIAL_ESCALATION)

## Layer states

| Layer | State |
|---|---|
| Labor | NORMAL |
| Activity | NORMAL |
| Credit | NORMAL |
| Forward | NORMAL |
| Shock | NORMAL |

## Selected current metrics

| Metric | Reading |
|---|---:|
| Sahm Rule | 0.00 pp |
| Three-month average payroll change | 75.0 thousand |
| Initial-claims rise from 52-week low | 1.3% |
| Contracting core activity series | 1 of 4 |
| CFNAI-MA3 | 0.03 |
| Baa-Treasury spread | 1.52% |
| High-yield OAS | 3.47% |
| NFCI | -0.478 |
| Permits, year over year | -8.4% |
| Housing starts, year over year | -0.8% |
| Oil, three-month change | 2.9% |

## Yield-curve decomposition

- Pattern: **FLATTENING**
- 10y-3m spread: 0.70%
- 20-trading-day spread change: -0.18 percentage points
- 20-trading-day 10-year change: -0.06 percentage points
- 20-trading-day 3-month change: 0.09 percentage points

The curve classification is contextual. It cannot independently elevate the overall state to Orange or Red. No positive spread level, including +1.0%, is itself a trigger.

## Data quality

Stale or missing series: `DRCRELEXFACBS`.

`release_date` remains null unless it is supplied by an authoritative machine-readable source. Raw payloads are retained and SHA-256 hashed.

## Interpretation boundary

This output is a deterministic economic-state classification. It does not automatically prescribe a portfolio allocation or trade.
