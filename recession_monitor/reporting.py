from __future__ import annotations

from typing import Any


def _fmt(value: Any, digits: int = 2, pct: bool = False) -> str:
    if value is None:
        return "n/a"
    if pct:
        return f"{100 * float(value):.{digits}f}%"
    return f"{float(value):.{digits}f}"


def current_report(snapshot: dict[str, Any]) -> str:
    m = snapshot["metrics"]
    q = snapshot["data_quality"]
    stale = [sid for sid, item in q.items() if item["status"] != "FRESH" and sid != "USREC"]
    fallbacks = [sid for sid, item in q.items() if item.get("retrieval_status") == "CACHE_FALLBACK"]
    lines = [
        "# Deterministic U.S. Recession Monitor",
        "",
        f"**As of:** {snapshot['as_of']}  ",
        f"**Ruleset:** `{snapshot['ruleset_version']}`  ",
        f"**Overall state:** **{snapshot['overall_state']}**",
        f"**Alert required:** **{'YES' if snapshot.get('alert', {}).get('required') else 'NO'}** ({snapshot.get('alert', {}).get('reason', 'n/a')})",
        "",
        "## Layer states",
        "",
        "| Layer | State |",
        "|---|---|",
    ]
    for layer, state in snapshot["layers"].items():
        lines.append(f"| {layer.title()} | {state} |")
    lines.extend([
        "",
        "## Selected current metrics",
        "",
        "| Metric | Reading |",
        "|---|---:|",
        f"| Sahm Rule | {_fmt(m['sahm'])} pp |",
        f"| Three-month average payroll change | {_fmt(m['payroll_3m_average_k'], 1)} thousand |",
        f"| Initial-claims rise from 52-week low | {_fmt(m['claims_ratio'], 1, pct=True)} |",
        f"| Contracting core activity series | {_fmt(m['activity_contracting_count'], 0)} of {_fmt(m['activity_available_count'], 0)} |",
        f"| CFNAI-MA3 | {_fmt(m['cfnai_ma3'])} |",
        f"| Baa-Treasury spread | {_fmt(m['baa_spread'])}% |",
        f"| High-yield OAS | {_fmt(m['hy_oas'])}% |",
        f"| NFCI | {_fmt(m['nfci'], 3)} |",
        f"| Permits, year over year | {_fmt(m['permits_yoy'], 1, pct=True)} |",
        f"| Housing starts, year over year | {_fmt(m['housing_starts_yoy'], 1, pct=True)} |",
        f"| Oil, three-month change | {_fmt(m['oil_3m_change'], 1, pct=True)} |",
        "",
        "## Yield-curve decomposition",
        "",
        f"- Pattern: **{snapshot['curve'].get('pattern', 'UNKNOWN')}**",
        f"- 10y-3m spread: {_fmt(snapshot['curve'].get('spread_percent'))}%",
        f"- 20-trading-day spread change: {_fmt(snapshot['curve'].get('change_20d_spread_percent'))} percentage points",
        f"- 20-trading-day 10-year change: {_fmt(snapshot['curve'].get('change_20d_10y_percent'))} percentage points",
        f"- 20-trading-day 3-month change: {_fmt(snapshot['curve'].get('change_20d_3m_percent'))} percentage points",
        "",
        "The curve classification is contextual. It cannot independently elevate the overall state to Orange or Red. No positive spread level, including +1.0%, is itself a trigger.",
        "",
        "## Data quality",
        "",
    ])
    if stale:
        lines.append("Stale or missing series: " + ", ".join(f"`{sid}`" for sid in stale) + ".")
    else:
        lines.append("All required live series are within their configured freshness windows.")
    if fallbacks:
        lines.append("Live retrieval failed and the retained hashed payload was used for: " + ", ".join(f"`{sid}`" for sid in fallbacks) + ". Freshness rules still apply.")
    lines.extend([
        "",
        "`release_date` remains null unless it is supplied by an authoritative machine-readable source. Raw payloads are retained and SHA-256 hashed.",
        "",
        "## Interpretation boundary",
        "",
        "This output is a deterministic economic-state classification. It does not automatically prescribe a portfolio allocation or trade.",
    ])
    return "\n".join(lines) + "\n"


def validation_report(result: dict[str, Any]) -> str:
    monthly = result["monthly_horizon_classification"]
    confusion = monthly["confusion_matrix"]
    events = result["recession_event_detection"]
    event_ci = events["event_detection_rate_interval"]
    alerts = result["alert_episode_analysis"]
    alert_ci = alerts["observed_episode_precision_interval"]
    lines = [
        "# Recession Monitor Validation Report",
        "",
        f"**Ruleset:** `{result['ruleset_version']}`  ",
        f"**Validation type:** {result['validation_type']}  ",
        f"**Coverage:** {result['coverage_start']} through {result['coverage_end']} ({result['months_tested']} months)",
        f"**Fully observed monthly prediction window:** through {monthly['evaluation_end']} ({monthly['months_evaluated']} months)",
        "",
        "## What is being measured",
        "",
        "This report deliberately separates three tests that have different units and denominators. They must not be combined into one hit rate.",
        "",
        "| Test | Unit | Question |",
        "|---|---|---|",
        "| Monthly horizon classification | Month | Was the state Orange/Red when recession was active or no more than 12 months away? |",
        "| Recession-event detection | NBER recession | Did any Orange/Red state occur inside the bounded lead/lag window? |",
        "| Alert-episode precision | Consolidated alert episode | Did an observed alert episode overlap or precede a recession? |",
        "",
        "## 1. Monthly horizon classification",
        "",
        monthly["target_definition"] + ".",
        "",
        "| Actual target / Engine state | Orange or Red | Green or Yellow | Total |",
        "|---|---:|---:|---:|",
        f"| Target positive | {confusion['true_positive_months']} | {confusion['false_negative_months']} | {monthly['target_positive_months']} |",
        f"| Target negative | {confusion['false_positive_months']} | {confusion['true_negative_months']} | {monthly['target_negative_months']} |",
        f"| Total | {confusion['true_positive_months'] + confusion['false_positive_months']} | {confusion['false_negative_months'] + confusion['true_negative_months']} | {monthly['months_evaluated']} |",
        "",
        "| Metric | Result | Denominator |",
        "|---|---:|---:|",
        f"| Monthly precision | {_fmt(monthly['precision'], 1, pct=True)} | {confusion['true_positive_months'] + confusion['false_positive_months']} Orange/Red months |",
        f"| Monthly recall | {_fmt(monthly['recall'], 1, pct=True)} | {monthly['target_positive_months']} target-positive months |",
        f"| Monthly specificity | {_fmt(monthly['specificity'], 1, pct=True)} | {monthly['target_negative_months']} target-negative months |",
        "",
        monthly["uncertainty_note"],
        "",
        "## 2. Recession-event detection",
        "",
        f"**Detected:** {events['episodes_detected']} of {events['episodes_eligible']} eligible recessions "
        f"({_fmt(events['event_detection_rate'], 1, pct=True)}).  ",
        f"**Exact 95% interval:** {_fmt(event_ci['lower'], 1, pct=True)} to {_fmt(event_ci['upper'], 1, pct=True)}.",
        "",
        events["definition"],
        "",
        "| NBER recession start | First Orange/Red | Lead (+) / lag (-), months | Detected |",
        "|---|---|---:|---|",
    ]
    for episode in events["episodes"]:
        lines.append(
            f"| {episode['recession_start']} | {episode['first_orange_or_red'] or 'None'} | "
            f"{episode['lead_lag_months'] if episode['lead_lag_months'] is not None else 'n/a'} | "
            f"{'Yes' if episode['detected'] else 'No'} |"
        )
    lines.extend([
        "",
        "## 3. Consolidated alert episodes",
        "",
        alerts["definition"],
        "",
        "| Result | Count |",
        "|---|---:|",
        f"| True-positive episodes | {alerts['true_positive_episodes']} |",
        f"| False-positive episodes | {alerts['false_positive_episodes']} |",
        f"| Right-censored episodes | {alerts['right_censored_episodes']} |",
        f"| Observed episode precision | {_fmt(alerts['observed_episode_precision'], 1, pct=True)} |",
        f"| Exact 95% interval | {_fmt(alert_ci['lower'], 1, pct=True)} to {_fmt(alert_ci['upper'], 1, pct=True)} |",
        "",
        "| Episode | Start | End | Peak | Alert months | Raw runs merged | Outcome | Context | Matched recession starts |",
        "|---:|---|---|---|---:|---:|---|---|---|",
    ])
    for episode in alerts["episodes"]:
        matches = ", ".join(episode["matched_recession_starts"]) or "None"
        lines.append(
            f"| {episode['episode']} | {episode['start']} | {episode['end']} | {episode['peak_state']} | "
            f"{episode['orange_or_red_months']} | {episode['raw_runs_merged']} | {episode['outcome']} | "
            f"{episode['context']} | {matches} |"
        )
    transitions = result["transition_diagnostics"]
    lines.extend([
        "",
        "## Transition diagnostics",
        "",
        f"There were {transitions['raw_orange_or_red_transition_count']} raw entries into Orange/Red. "
        + transitions["interpretation"],
        "",
        ", ".join(transitions["raw_orange_or_red_transition_dates"]),
        "",
        "## State occupancy",
        "",
        "| State | Months |",
        "|---|---:|",
    ])
    for state, months in sorted(result["state_months"].items()):
        lines.append(f"| {state} | {months} |")
    lines.extend(["", "## Material caveats", ""])
    for caveat in result["material_caveats"]:
        lines.append(f"- {caveat}")
    lines.extend([
        "",
        "## Readiness",
        "",
        "**Share with caveats; not ready for portfolio decision use.** The engine is deterministic and reproducible from retained inputs, and the three validation questions are now explicit. Historical revision leakage remains unresolved.",
    ])
    return "\n".join(lines) + "\n"


def quality_report(snapshot: dict[str, Any], registry: dict, metadata: dict[str, dict]) -> str:
    lines = [
        "# Recession Monitor Data-Quality Report",
        "",
        f"**As of:** {snapshot['as_of']}  ",
        f"**Registry:** `{snapshot['registry_version']}`  ",
        "",
        "## Source coverage and freshness",
        "",
        "| Series | Layer | Coverage | Last observation | Freshness | Retrieval | Observations |",
        "|---|---|---|---|---|---|---:|",
    ]
    for sid, spec in registry["series"].items():
        meta = metadata.get(sid, {})
        quality = snapshot["data_quality"].get(sid, {})
        coverage = f"{meta.get('first_observation', 'n/a')} to {meta.get('last_observation', 'n/a')}"
        lines.append(
            f"| `{sid}` | {spec['layer']} | {coverage} | {quality.get('last_observation', 'n/a')} | "
            f"{quality.get('status', 'UNKNOWN')} | {meta.get('retrieval_status', 'n/a')} | {meta.get('observation_count', 'n/a')} |"
        )
    lines.extend([
        "",
        "## Material findings",
        "",
        "- Every downloaded payload is retained unchanged and identified by a SHA-256 hash.",
        "- Duplicate observation dates are deterministically resolved by retaining the last row after numeric parsing.",
        "- Missing values are preserved during ingestion. The live engine excludes stale series using the registry's explicit freshness window.",
        "- `release_date` is null because the FRED observations API payload does not provide authoritative release timestamps.",
        "- `BAMLH0A0HYM2` has limited trailing redistribution history; `BAA10Y` is used as the long-history corporate-credit proxy.",
        "- `PCEC96` begins in 2007, so earlier activity breadth relies on the other available core series and CFNAI.",
        "- Historical validation uses revised observations and is not vintage-correct. This is the largest unresolved methodological limitation.",
        "- A live request failure may use the retained hashed payload only when explicitly enabled. The retrieval is labeled `CACHE_FALLBACK`; observation-age rules still determine freshness and can force `UNKNOWN`.",
        "- Commercial real-estate delinquency is treated as corroboration-only because it is quarterly and lagging; it cannot set or upgrade the credit state.",
        "",
        "## Readiness",
        "",
        "**Ready for deterministic research use; not ready for decision use.** Live freshness, source identity and reproducibility are controlled. Historical revision leakage remains unresolved.",
    ])
    return "\n".join(lines) + "\n"
