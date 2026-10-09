# Deterministic U.S. Recession Monitor

**As of:** 2026-10-09  
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
| Three-month average payroll change | 54.0 thousand |
| Initial-claims rise from 52-week low | 0.0% |
| Contracting core activity series | 1 of 4 |
| CFNAI-MA3 | 0.01 |
| Baa-Treasury spread | 1.46% |
| High-yield OAS | 3.09% |
| NFCI | -0.494 |
| Permits, year over year | -1.1% |
| Housing starts, year over year | 0.2% |
| Oil, three-month change | 11.7% |

## Yield-curve decomposition

- Pattern: **STABLE**
- 10y-3m spread: 0.99%
- 20-trading-day spread change: 0.04 percentage points
- 20-trading-day 10-year change: 0.33 percentage points
- 20-trading-day 3-month change: 0.22 percentage points

The curve classification is contextual. It cannot independently elevate the overall state to Orange or Red. No positive spread level, including +1.0%, is itself a trigger.

## Data quality

Stale or missing series: `DRCRELEXFACBS`.

`release_date` remains null unless it is supplied by an authoritative machine-readable source. Raw payloads are retained and SHA-256 hashed.

## Interpretation boundary

This output is a deterministic economic-state classification. It does not automatically prescribe a portfolio allocation or trade.
