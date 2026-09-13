# Verification Receipt

**Ruleset:** `0.1.1-provisional`  
**Package:** `0.1.2`  
**Registry:** `0.1.1` (`FRED API v1`)  
**As-of date:** 2026-09-13  
**Validation status:** Share with caveats; not ready for portfolio decision use

## Completed checks

- All 22 automated tests passed, including authenticated FRED JSON parsing, missing/rejected-key failure, secret redaction, immutable vintage handling, and labeled fallback after an ordinary live retrieval failure.
- Two successive offline runs produced byte-identical current output, validation output, indicator history, and generated reports.
- The authenticated GitHub Actions run retrieved all 24 allowlisted series `LIVE`; all 24 passed their explicit freshness checks and no API key field was written to committed metadata.
- The monthly confusion matrix was independently recomputed directly from `indicator_history.csv` and the retained `USREC` source payload. It reconciled exactly: TP 105, FP 54, FN 75, TN 468.
- The archived `0.1.0-provisional` output remains available for before-and-after comparison.

## Deterministic output hashes

| File | SHA-256 |
|---|---|
| `outputs/latest.json` | `d880b51efaf7226037e1fd24a751824812c5d869eb2837e3612a80c56d9b4021` |
| `outputs/validation.json` | `fb56feb58c66d313fbe8ba961c910c7a15b167f23d3e14a77dcf5f41b8874531` |
| `outputs/indicator_history.csv` | `6db45027b474b07795648205b82006ac543144c133d8ffb906e4faa09387c26b` |
| `reports/current_report.md` | `f011c6fc3fc27f7b219f063fd22b80458e3a20191176725975eda9932da59788` |
| `reports/data_quality_report.md` | `54c5760b52a799c03e96b8b45c647b2a4416797a5d273e45ba87536dc94f6c84` |
| `reports/validation_report.md` | `fe45b79b011e8bf610688cab81ae3458194de2c0c4b72cad8af2601ffc631163` |
| `outputs/source_metadata.json` | `f3f3ba9e900eed32beacfff0c577284a4ff86c78887d8280f52facdbea1d5e9a` |

## Unresolved validation risk

The historical test still uses latest-revised observations and reconstructed monthly anchors rather than the information set available on each historical release date. The exact hashes establish reproducibility of this package; they do not eliminate revision leakage. Decision-grade validation still requires ALFRED vintages or a sufficiently long prospectively frozen archive.
