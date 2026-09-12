# Recession Monitor Data-Quality Report

**As of:** 2026-09-12  
**Registry:** `0.1.0`  

## Source coverage and freshness

| Series | Layer | Coverage | Last observation | Freshness | Observations |
|---|---|---|---|---|---:|
| `SAHMREALTIME` | labor | 1959-12-01 to 2026-08-01 | 2026-08-01 | FRESH | 800 |
| `UNRATE` | labor | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | 811 |
| `PAYEMS` | labor | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | 812 |
| `IC4WSA` | labor | 1967-01-28 to 2026-09-05 | 2026-09-05 | FRESH | 3111 |
| `CCSA` | labor | 1967-01-07 to 2026-08-29 | 2026-08-29 | FRESH | 3113 |
| `W875RX1` | activity | 1959-01-01 to 2026-07-01 | 2026-07-01 | FRESH | 811 |
| `PCEC96` | activity | 2007-01-01 to 2026-07-01 | 2026-07-01 | FRESH | 235 |
| `INDPRO` | activity | 1959-01-01 to 2026-07-01 | 2026-07-01 | FRESH | 811 |
| `CMRMTSPL` | activity | 1967-01-01 to 2026-06-01 | 2026-06-01 | FRESH | 714 |
| `CFNAIMA3` | activity | 1967-05-01 to 2026-07-01 | 2026-07-01 | FRESH | 711 |
| `PERMIT` | forward | 1960-01-01 to 2026-07-01 | 2026-07-01 | FRESH | 799 |
| `HOUST` | forward | 1959-01-01 to 2026-07-01 | 2026-07-01 | FRESH | 811 |
| `DGS10` | curve | 1962-01-02 to 2026-09-10 | 2026-09-10 | FRESH | 16158 |
| `DGS3MO` | curve | 1981-09-01 to 2026-09-10 | 2026-09-10 | FRESH | 11256 |
| `T10Y3M` | curve | 1982-01-04 to 2026-09-11 | 2026-09-11 | FRESH | 11176 |
| `BAA10Y` | credit | 1986-01-02 to 2026-09-10 | 2026-09-10 | FRESH | 10173 |
| `BAMLH0A0HYM2` | credit | 2023-09-12 to 2026-09-10 | 2026-09-10 | FRESH | 787 |
| `NFCI` | credit | 1971-01-08 to 2026-09-04 | 2026-09-04 | FRESH | 2905 |
| `STLFSI4` | credit | 1993-12-31 to 2026-09-04 | 2026-09-04 | FRESH | 1706 |
| `DRCRELEXFACBS` | credit | 1991-01-01 to 2026-04-01 | 2026-04-01 | FRESH | 142 |
| `DFII10` | shock | 2003-01-02 to 2026-09-10 | 2026-09-10 | FRESH | 5927 |
| `T10YIE` | shock | 2003-01-02 to 2026-09-11 | 2026-09-11 | FRESH | 5928 |
| `DCOILWTICO` | shock | 1986-01-02 to 2026-09-09 | 2026-09-09 | FRESH | 10241 |
| `USREC` | validation | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | 812 |

## Material findings

- Every downloaded payload is retained unchanged and identified by a SHA-256 hash.
- Duplicate observation dates are deterministically resolved by retaining the last row after numeric parsing.
- Missing values are preserved during ingestion. The live engine excludes stale series using the registry's explicit freshness window.
- `release_date` is null because the FRED CSV endpoint does not provide authoritative release timestamps in the payload.
- `BAMLH0A0HYM2` has limited trailing redistribution history; `BAA10Y` is used as the long-history corporate-credit proxy.
- `PCEC96` begins in 2007, so earlier activity breadth relies on the other available core series and CFNAI.
- Historical validation uses revised observations and is not vintage-correct. This is the largest unresolved methodological limitation.
- Commercial real-estate delinquency is treated as corroboration-only because it is quarterly and lagging; it cannot set or upgrade the credit state.

## Readiness

**Ready for deterministic research use; not ready for decision use.** Live freshness, source identity and reproducibility are controlled. Historical revision leakage remains unresolved.
