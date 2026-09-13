from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path

from .alert import alert_decision
from .config import load_yaml
from .engine import build_features, live_snapshot
from .fetch import fetch_registry
from .reporting import current_report, quality_report, validation_report
from .validation import validate_history


def run(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    registry = load_yaml(root / "config" / "series.yaml")
    rules = load_yaml(root / "config" / "rules.yaml")
    raw_dir = root / "data" / "raw"
    output_dir = root / "outputs"
    report_dir = root / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    data, metadata = fetch_registry(
        registry,
        start=args.start,
        raw_dir=raw_dir,
        metadata_path=output_dir / "source_metadata.json",
        offline=args.offline,
        vintage_dir=(
            None
            if args.offline or args.no_vintage_copy
            else root / "data" / "vintages" / date.today().isoformat()
        ),
        workers=args.workers,
        download_attempts=args.download_attempts,
        download_timeout=args.download_timeout,
        allow_cache_fallback=args.allow_cache_fallback,
        api_key=os.environ.get("FRED_API_KEY"),
    )
    as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
    latest_path = output_dir / "latest.json"
    previous = json.loads(latest_path.read_text(encoding="utf-8")) if latest_path.exists() else None
    snapshot, _ = live_snapshot(data, registry, rules, metadata, as_of)
    snapshot["alert"] = alert_decision(previous, snapshot)
    latest_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    snapshot_dir = output_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / f"{as_of.isoformat()}.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    (report_dir / "current_report.md").write_text(current_report(snapshot), encoding="utf-8")
    (report_dir / "data_quality_report.md").write_text(quality_report(snapshot, registry, metadata), encoding="utf-8")

    historical = build_features(data, rules)
    historical.reset_index(names="month").to_csv(output_dir / "indicator_history.csv", index=False)
    validation = validate_history(historical, data["USREC"], rules)
    (output_dir / "validation.json").write_text(json.dumps(validation, indent=2, sort_keys=True), encoding="utf-8")
    (report_dir / "validation_report.md").write_text(validation_report(validation), encoding="utf-8")
    print(json.dumps({
        "overall_state": snapshot["overall_state"],
        "as_of": snapshot["as_of"],
        "curve_pattern": snapshot["curve"].get("pattern"),
        "ruleset": snapshot["ruleset_version"],
        "monthly_horizon_precision": validation["monthly_horizon_classification"]["precision"],
        "monthly_horizon_recall": validation["monthly_horizon_classification"]["recall"],
        "recession_episodes_detected": validation["recession_event_detection"]["episodes_detected"],
        "recession_episodes_eligible": validation["recession_event_detection"]["episodes_eligible"],
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic U.S. recession monitor")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--start", default="1959-01-01")
    parser.add_argument("--as-of", default=None, help="ISO date; defaults to today's date")
    parser.add_argument("--offline", action="store_true", help="Use retained raw CSV snapshots")
    parser.add_argument(
        "--no-vintage-copy",
        action="store_true",
        help="Skip expanded vintage copies when committed data/raw history is retained by version control",
    )
    parser.add_argument("--workers", type=int, default=6, help="Maximum parallel source requests")
    parser.add_argument("--download-attempts", type=int, default=3, help="Attempts per live source request")
    parser.add_argument("--download-timeout", type=int, default=45, help="Seconds allowed per live source request")
    parser.add_argument(
        "--allow-cache-fallback",
        action="store_true",
        help="Use the retained hashed payload after a live request failure; normal freshness rules still apply",
    )
    return parser


def main() -> int:
    return run(build_parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
