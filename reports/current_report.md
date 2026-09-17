# Deterministic U.S. Recession Monitor

**As of:** 2026-09-17  
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
| Shock | SEVERE |

## Selected current metrics

| Metric | Reading |
|---|---:|
| Sahm Rule | -0.07 pp |
| Three-month average payroll change | 61.0 thousand |
| Initial-claims rise from 52-week low | 2.1% |
| Contracting core activity series | 0 of 3 |
| CFNAI-MA3 | -0.04 |
| Baa-Treasury spread | 1.48% |
| High-yield OAS | 2.76% |
| NFCI | -0.560 |
| Permits, year over year | -3.5% |
| Housing starts, year over year | -3.3% |
| Oil, three-month change | 51.7% |

## Yield-curve decomposition

- Pattern: **STABLE**
- 10y-3m spread: 0.87%
- 20-trading-day spread change: 0.02 percentage points
- 20-trading-day 10-year change: 0.29 percentage points
- 20-trading-day 3-month change: 0.25 percentage points

The curve classification is contextual. It cannot independently elevate the overall state to Orange or Red. No positive spread level, including +1.0%, is itself a trigger.

## Data quality

Stale or missing series: `INDPRO`.

`release_date` remains null unless it is supplied by an authoritative machine-readable source. Raw payloads are retained and SHA-256 hashed.

## Interpretation boundary

This output is a deterministic economic-state classification. It does not automatically prescribe a portfolio allocation or trade.
