# Verification Receipt

**Ruleset:** `0.1.1-provisional`  
**As-of date:** 2026-09-12  
**Validation status:** Share with caveats; not ready for portfolio decision use

## Completed checks

- All 18 automated tests passed, including CRE corroboration behavior, curve classification, alert transitions, alert-episode consolidation, exact confidence intervals, immutable vintage conflict handling, and labeled fallback to retained data after a live retrieval failure.
- Two successive offline runs produced byte-identical current output, validation output, indicator history, and generated reports.
- The monthly confusion matrix was independently recomputed directly from `indicator_history.csv` and the retained `USREC.csv` payload. It reconciled exactly: TP 105, FP 54, FN 75, TN 468.
- The archived `0.1.0-provisional` output remains available for before-and-after comparison.

## Deterministic output hashes

| File | SHA-256 |
|---|---|
| `outputs/latest.json` | `371626b6d7a6b75655579fe05878186ca84f1d1f14db4e30f1983d9ffc6ab6f2` |
| `outputs/validation.json` | `fb56feb58c66d313fbe8ba961c910c7a15b167f23d3e14a77dcf5f41b8874531` |
| `outputs/indicator_history.csv` | `6db45027b474b07795648205b82006ac543144c133d8ffb906e4faa09387c26b` |
| `reports/current_report.md` | `1da0dae2c293b49f7892fb6ad87a239446e82d2b7822df80728fbb6eefde2957` |
| `reports/data_quality_report.md` | `8eb051b0bd79dd85a93c3fab6361b76fe1bc1bdcc4c59048b7b3a0846752a8ac` |
| `reports/validation_report.md` | `fe45b79b011e8bf610688cab81ae3458194de2c0c4b72cad8af2601ffc631163` |
| `outputs/source_metadata.json` | `b00d4b0f47058722e07321af1a6f0116bb2af41734ef751180df54067ae65e74` |

## Unresolved validation risk

The historical test still uses latest-revised observations and reconstructed monthly anchors rather than the information set available on each historical release date. The exact hashes establish reproducibility of this package; they do not eliminate revision leakage. Decision-grade validation still requires ALFRED vintages or a sufficiently long prospectively frozen archive.
