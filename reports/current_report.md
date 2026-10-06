# Deterministic U.S. Recession Monitor

**As of:** 2026-10-06  
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
| Shock | ELEVATED |

## Selected current metrics

| Metric | Reading |
|---|---:|
| Sahm Rule | 0.00 pp |
| Three-month average payroll change | 54.0 thousand |
| Initial-claims rise from 52-week low | 0.5% |
| Contracting core activity series | 1 of 4 |
| CFNAI-MA3 | 0.01 |
| Baa-Treasury spread | 1.47% |
| High-yield OAS | 3.10% |
| NFCI | -0.548 |
| Permits, year over year | -1.1% |
| Housing starts, year over year | 0.2% |
| Oil, three-month change | 11.6% |

## Yield-curve decomposition

- Pattern: **BEAR_STEEPENER**
- 10y-3m spread: 1.09%
- 20-trading-day spread change: 0.22 percentage points
- 20-trading-day 10-year change: 0.50 percentage points
- 20-trading-day 3-month change: 0.28 percentage points

The curve classification is contextual. It cannot independently elevate the overall state to Orange or Red. No positive spread level, including +1.0%, is itself a trigger.

## Data quality

All required live series are within their configured freshness windows.

`release_date` remains null unless it is supplied by an authoritative machine-readable source. Raw payloads are retained and SHA-256 hashed.

## Interpretation boundary

This output is a deterministic economic-state classification. It does not automatically prescribe a portfolio allocation or trade.
