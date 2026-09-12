# Deterministic U.S. Recession Monitor

This project converts the recession-monitoring taxonomy into an executable, versioned state engine. The classifier is deterministic: the same retained raw payloads and the same ruleset version produce the same output.

## Design boundary

The model classifies economic evidence; it does not forecast with an LLM and does not prescribe a portfolio trade. Market warnings cannot independently produce an Orange or Red recession state.

The pipeline is:

1. Fetch an allowlisted set of FRED CSV series.
2. Retain the exact raw payload and compute its SHA-256 hash.
   Online runs also create an immutable date-stamped copy under `data/vintages/`; a conflicting payload for the same capture date fails closed.
3. Transform observations with fixed, documented formulas.
4. Classify each layer as `NORMAL`, `ELEVATED`, `SEVERE`, or `UNKNOWN`.
5. Apply explicit cross-layer rules to produce `GREEN`, `YELLOW`, `ORANGE`, or `RED`.
6. Write machine-readable output and human-readable reports.

## Run

From the project directory:

```bash
python3 -m recession_monitor.cli --as-of 2026-09-12
```

Reproduce the result from retained source files without any network requests:

```bash
python3 -m recession_monitor.cli --as-of 2026-09-12 --offline
```

Scheduled runs and human-authored pushes execute the live monitor. Bot-authored output commits do not rerun the live job, preventing commit loops. The workflow uses `--no-vintage-copy` to avoid duplicate working-tree payloads. Each fetched `data/raw` file and its SHA-256 receipt are committed, making Git history the point-in-time archive.

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

## Outputs

- `outputs/latest.json`: current deterministic classification and complete data-quality receipt.
- `outputs/snapshots/YYYY-MM-DD.json`: dated state snapshots used for transition auditing.
- `outputs/source_metadata.json`: retrieval metadata, coverage and payload hashes.
- `outputs/indicator_history.csv`: historical features and states.
- `outputs/validation.json`: machine-readable historical validation.
- `reports/current_report.md`: current readable assessment.
- `reports/data_quality_report.md`: source coverage, freshness and revision-risk audit.
- `reports/validation_report.md`: false-positive, detection and caveat report.
- `reports/methodology_changes_v0.1.1.md`: auditable rule and metric-definition change note with before/after results.
- `reports/verification_receipt.md`: tests, independent metric reconciliation, deterministic rerun result, and output hashes.
- `archive/v0.1.0-provisional/`: preserved prior rules, outputs, and reports.

## Rule hierarchy

- **GREEN:** no broad deterioration.
- **YELLOW:** at least two independent layers are elevated.
- **ORANGE:** labor is elevated and activity or credit confirms.
- **RED:** labor and activity are severe, or severe credit stress is joined by deteriorating activity.

The curve is separately classified as `BULL_STEEPENER`, `BEAR_STEEPENER`, `MIXED_STEEPENER`, `FLATTENING`, `STABLE`, or `UNKNOWN`. It cannot independently control the overall state, and no absolute positive spread level—including +1.0%—is a trigger.

An alert is emitted only when the overall state escalates, a layer newly becomes Severe, or a core source becomes stale after previously being fresh. The initial run establishes a baseline and does not alert.

## Data and revision policy

The registry is fixed in `config/series.yaml`; thresholds are fixed in `config/rules.yaml`. Missing or stale core inputs become `UNKNOWN`, never `NORMAL`.

The historical validation uses current revised FRED history and is therefore a pseudo-real-time test. It is useful for finding obvious rule failures, but it is not decision-grade. The report keeps three different questions separate: monthly horizon classification, NBER recession-event detection, and consolidated alert-episode precision. Raw state transitions are diagnostics, not independent forecasts.

True historical reproducibility requires ALFRED vintages or a sufficiently long archive of prospectively retained raw snapshots. In GitHub, successive committed `data/raw` versions provide that prospective archive without duplicating every payload under a new date directory. `release_date` remains null unless supplied by an authoritative machine-readable source.

## Threshold status

Ruleset `0.1.1-provisional` preserves the original numerical thresholds but changes commercial real-estate delinquency to a corroboration-only credit indicator. Its quarterly, lagging reading cannot set or upgrade the credit state; it is retained as context alongside primary market and financial-condition evidence. The archived `0.1.0-provisional` outputs remain under `archive/` for exact comparison.

The Sahm Rule 0.50 trigger and the CFNAI -0.70 historical recession guideline come from their published methodologies. Other thresholds are explicit hypotheses and must earn their place through validation; they are not represented as official recession definitions.
