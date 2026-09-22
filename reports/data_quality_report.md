# Recession Monitor Data-Quality Report

**As of:** 2026-09-22  
**Registry:** `0.1.1`  

## Source coverage and freshness

| Series | Layer | Coverage | Last observation | Freshness | Retrieval | Observations |
|---|---|---|---|---|---|---:|
| `SAHMREALTIME` | labor | 1959-12-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 800 |
| `UNRATE` | labor | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 811 |
| `PAYEMS` | labor | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 812 |
| `IC4WSA` | labor | 1967-01-28 to 2026-09-12 | 2026-09-12 | FRESH | LIVE | 3112 |
| `CCSA` | labor | 1967-01-07 to 2026-09-05 | 2026-09-05 | FRESH | LIVE | 3114 |
| `W875RX1` | activity | 1959-01-01 to 2026-07-01 | 2026-07-01 | FRESH | LIVE | 811 |
| `PCEC96` | activity | 2007-01-01 to 2026-07-01 | 2026-07-01 | FRESH | LIVE | 235 |
| `INDPRO` | activity | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 812 |
| `CMRMTSPL` | activity | 1967-01-01 to 2026-06-01 | 2026-06-01 | FRESH | LIVE | 714 |
| `CFNAIMA3` | activity | 1967-05-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 712 |
| `PERMIT` | forward | 1960-01-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 800 |
| `HOUST` | forward | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 812 |
| `DGS10` | curve | 1962-01-02 to 2026-09-18 | 2026-09-18 | FRESH | LIVE | 16164 |
| `DGS3MO` | curve | 1981-09-01 to 2026-09-18 | 2026-09-18 | FRESH | LIVE | 11262 |
| `T10Y3M` | curve | 1982-01-04 to 2026-09-21 | 2026-09-21 | FRESH | LIVE | 11182 |
| `BAA10Y` | credit | 1986-01-02 to 2026-09-18 | 2026-09-18 | FRESH | LIVE | 10179 |
| `BAMLH0A0HYM2` | credit | 2023-09-22 to 2026-09-18 | 2026-09-18 | FRESH | LIVE | 785 |
| `NFCI` | credit | 1971-01-08 to 2026-09-11 | 2026-09-11 | FRESH | LIVE | 2906 |
| `STLFSI4` | credit | 1993-12-31 to 2026-09-11 | 2026-09-11 | FRESH | LIVE | 1707 |
| `DRCRELEXFACBS` | credit | 1991-01-01 to 2026-04-01 | 2026-04-01 | FRESH | LIVE | 142 |
| `DFII10` | shock | 2003-01-02 to 2026-09-18 | 2026-09-18 | FRESH | LIVE | 5933 |
| `T10YIE` | shock | 2003-01-02 to 2026-09-21 | 2026-09-21 | FRESH | LIVE | 5934 |
| `DCOILWTICO` | shock | 1986-01-02 to 2026-09-15 | 2026-09-15 | FRESH | LIVE | 9502 |
| `USREC` | validation | 1959-01-01 to 2026-08-01 | 2026-08-01 | FRESH | LIVE | 812 |

## Material findings

- Every downloaded payload is retained unchanged and identified by a SHA-256 hash.
- Duplicate observation dates are deterministically resolved by retaining the last row after numeric parsing.
- Missing values are preserved during ingestion. The live engine excludes stale series using the registry's explicit freshness window.
- `release_date` is null because the FRED observations API payload does not provide authoritative release timestamps.
- `BAMLH0A0HYM2` has limited trailing redistribution history; `BAA10Y` is used as the long-history corporate-credit proxy.
- `PCEC96` begins in 2007, so earlier activity breadth relies on the other available core series and CFNAI.
- Historical validation uses revised observations and is not vintage-correct. This is the largest unresolved methodological limitation.
- A live request failure may use the retained hashed payload only when explicitly enabled. The retrieval is labeled `CACHE_FALLBACK`; observation-age rules still determine freshness and can force `UNKNOWN`.
- Commercial real-estate delinquency is treated as corroboration-only because it is quarterly and lagging; it cannot set or upgrade the credit state.

## Readiness

**Ready for deterministic research use; not ready for decision use.** Live freshness, source identity and reproducibility are controlled. Historical revision leakage remains unresolved.
