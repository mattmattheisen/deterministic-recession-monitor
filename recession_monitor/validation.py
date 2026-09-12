from __future__ import annotations

from math import comb
from typing import Any

import pandas as pd

from .constants import OVERALL_RANK


def _future_recession_target(usrec: pd.Series, horizon: int) -> pd.Series:
    """True when recession is active or its start is within `horizon` months."""
    starts = usrec.eq(1) & usrec.shift(1, fill_value=0).eq(0)
    result = pd.Series(False, index=usrec.index)
    start_dates = list(usrec.index[starts])
    for current in usrec.index:
        future_limit = current + pd.DateOffset(months=horizon)
        result.loc[current] = bool(
            usrec.loc[current] == 1
            or any(current < start <= future_limit for start in start_dates)
        )
    return result


def _safe_ratio(num: int, den: int) -> float | None:
    return None if den == 0 else round(num / den, 4)


def _binomial_tail_at_least(successes: int, trials: int, probability: float) -> float:
    return sum(
        comb(trials, k) * probability**k * (1.0 - probability) ** (trials - k)
        for k in range(successes, trials + 1)
    )


def _binomial_cdf_at_most(successes: int, trials: int, probability: float) -> float:
    return sum(
        comb(trials, k) * probability**k * (1.0 - probability) ** (trials - k)
        for k in range(0, successes + 1)
    )


def exact_binomial_interval(successes: int, trials: int, confidence: float = 0.95) -> dict[str, float | int | str | None]:
    """Two-sided Clopper-Pearson interval without a SciPy dependency."""
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("Expected 0 <= successes <= trials")
    if trials == 0:
        return {
            "method": "Clopper-Pearson exact",
            "confidence": confidence,
            "successes": successes,
            "trials": trials,
            "lower": None,
            "upper": None,
        }
    alpha_tail = (1.0 - confidence) / 2.0
    if successes == 0:
        lower = 0.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if _binomial_tail_at_least(successes, trials, mid) < alpha_tail:
                lo = mid
            else:
                hi = mid
        lower = (lo + hi) / 2.0
    if successes == trials:
        upper = 1.0
    else:
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2.0
            if _binomial_cdf_at_most(successes, trials, mid) > alpha_tail:
                lo = mid
            else:
                hi = mid
        upper = (lo + hi) / 2.0
    return {
        "method": "Clopper-Pearson exact",
        "confidence": confidence,
        "successes": successes,
        "trials": trials,
        "lower": round(lower, 4),
        "upper": round(upper, 4),
    }


def consolidate_alert_runs(active: pd.Series, cooldown_months: int) -> list[dict[str, Any]]:
    """Merge Orange/Red runs separated by at most the configured cooldown."""
    active = active.fillna(False).astype(bool)
    starts = list(active.index[active & ~active.shift(1, fill_value=False)])
    ends = list(active.index[active & ~active.shift(-1, fill_value=False)])
    runs: list[dict[str, Any]] = []
    for start, end in zip(starts, ends):
        active_months = int(active.loc[start:end].sum())
        if runs:
            previous_end = runs[-1]["end"]
            quiet_months = int((start.to_period("M") - previous_end.to_period("M")).n) - 1
            if quiet_months <= cooldown_months:
                runs[-1]["end"] = end
                runs[-1]["active_months"] += active_months
                runs[-1]["raw_runs_merged"] += 1
                continue
        runs.append({
            "start": start,
            "end": end,
            "active_months": active_months,
            "raw_runs_merged": 1,
        })
    return runs


def _recession_start_for_date(usrec: pd.Series, date: pd.Timestamp, starts: list[pd.Timestamp]) -> pd.Timestamp | None:
    if usrec.loc[date] != 1:
        return None
    candidates = [start for start in starts if start <= date]
    return candidates[-1] if candidates else None


def _alert_episode_analysis(frame: pd.DataFrame, rules: dict) -> dict[str, Any]:
    cooldown = int(rules["validation"]["alert_episode_cooldown_months"])
    forecast_months = int(rules["validation"]["alert_episode_forecast_months"])
    runs = consolidate_alert_runs(frame["orange_or_red"], cooldown)
    recession_starts = list(frame.index[frame["usrec"].eq(1) & frame["usrec"].shift(1, fill_value=0).eq(0)])
    recession_exits = list(frame.index[frame["usrec"].eq(0) & frame["usrec"].shift(1, fill_value=0).eq(1)])
    episodes = []
    for number, run in enumerate(runs, start=1):
        forecast_end = run["start"] + pd.DateOffset(months=forecast_months)
        matched = {
            start for start in recession_starts
            if run["start"] <= start <= forecast_end
        }
        recession_alert_months = frame.loc[run["start"]:run["end"]]
        recession_alert_months = recession_alert_months.index[
            recession_alert_months["orange_or_red"] & recession_alert_months["usrec"].eq(1)
        ]
        for alert_month in recession_alert_months:
            matched_start = _recession_start_for_date(frame["usrec"], alert_month, recession_starts)
            if matched_start is not None:
                matched.add(matched_start)
        if matched:
            outcome = "TRUE_POSITIVE"
            context = "MATCHED_RECESSION"
        elif forecast_end > frame.index.max():
            outcome = "RIGHT_CENSORED"
            context = "OUTCOME_NOT_YET_OBSERVABLE"
        else:
            outcome = "FALSE_POSITIVE"
            prior_exits = [date for date in recession_exits if date <= run["start"]]
            months_since_exit = None if not prior_exits else int(
                (run["start"].to_period("M") - prior_exits[-1].to_period("M")).n
            )
            context = (
                "POST_RECESSION_AFTERSHOCK"
                if months_since_exit is not None and months_since_exit <= forecast_months
                else "UNMATCHED_STRESS"
            )
        peak_state = max(
            frame.loc[run["start"]:run["end"], "overall_state"],
            key=lambda state: OVERALL_RANK[state],
        )
        calendar_months = int((run["end"].to_period("M") - run["start"].to_period("M")).n) + 1
        episodes.append({
            "episode": number,
            "start": run["start"].date().isoformat(),
            "end": run["end"].date().isoformat(),
            "calendar_months": calendar_months,
            "orange_or_red_months": run["active_months"],
            "raw_runs_merged": run["raw_runs_merged"],
            "peak_state": peak_state,
            "outcome": outcome,
            "context": context,
            "start_layers": {
                "labor": frame.loc[run["start"], "labor_state"],
                "activity": frame.loc[run["start"], "activity_state"],
                "credit": frame.loc[run["start"], "credit_state"],
            },
            "matched_recession_starts": [date.date().isoformat() for date in sorted(matched)],
        })
    true_positive = sum(item["outcome"] == "TRUE_POSITIVE" for item in episodes)
    false_positive = sum(item["outcome"] == "FALSE_POSITIVE" for item in episodes)
    right_censored = sum(item["outcome"] == "RIGHT_CENSORED" for item in episodes)
    observed = true_positive + false_positive
    return {
        "definition": (
            f"Orange/Red runs separated by {cooldown} or fewer non-alert months are one episode. "
            f"An observed episode is positive if it overlaps a recession or is followed by a recession start within {forecast_months} months."
        ),
        "cooldown_months": cooldown,
        "forecast_window_months": forecast_months,
        "true_positive_episodes": true_positive,
        "false_positive_episodes": false_positive,
        "right_censored_episodes": right_censored,
        "observed_episode_precision": _safe_ratio(true_positive, observed),
        "observed_episode_precision_interval": exact_binomial_interval(true_positive, observed),
        "episodes": episodes,
    }


def validate_history(features: pd.DataFrame, usrec: pd.Series, rules: dict) -> dict[str, Any]:
    recession = usrec.resample("ME").last().reindex(features.index).ffill()
    frame = features[["overall_state", "labor_state", "activity_state", "credit_state"]].copy()
    frame["usrec"] = recession
    frame = frame.loc[frame["overall_state"].ne("UNKNOWN") & frame["usrec"].notna()].copy()
    if frame.empty:
        raise ValueError("No overlapping history for validation")
    horizon = int(rules["validation"]["prediction_horizon_months"])
    lookback = int(rules["validation"]["episode_lookback_months"])
    lag_window = int(rules["validation"]["episode_detection_lag_months"])
    frame["target"] = _future_recession_target(frame["usrec"], horizon)
    frame["orange_or_red"] = frame["overall_state"].map(OVERALL_RANK).ge(2)

    evaluation_end = frame.index.max() - pd.DateOffset(months=horizon)
    evaluation = frame.loc[frame.index <= evaluation_end].copy()
    tp = int((evaluation["orange_or_red"] & evaluation["target"]).sum())
    fp = int((evaluation["orange_or_red"] & ~evaluation["target"]).sum())
    fn = int((~evaluation["orange_or_red"] & evaluation["target"]).sum())
    tn = int((~evaluation["orange_or_red"] & ~evaluation["target"]).sum())
    monthly = {
        "unit": "month",
        "positive_classification": "overall state is ORANGE or RED",
        "target_definition": f"NBER recession is active or a recession begins within the next {horizon} months",
        "evaluation_end": evaluation.index.max().date().isoformat(),
        "months_evaluated": int(len(evaluation)),
        "target_positive_months": tp + fn,
        "target_negative_months": fp + tn,
        "confusion_matrix": {
            "true_positive_months": tp,
            "false_positive_months": fp,
            "false_negative_months": fn,
            "true_negative_months": tn,
        },
        "precision": _safe_ratio(tp, tp + fp),
        "recall": _safe_ratio(tp, tp + fn),
        "specificity": _safe_ratio(tn, tn + fp),
        "uncertainty_note": "No naive binomial interval is reported because adjacent monthly observations are serially dependent.",
    }

    starts = frame["usrec"].eq(1) & frame["usrec"].shift(1, fill_value=0).eq(0)
    ends = frame["usrec"].eq(0) & frame["usrec"].shift(1, fill_value=0).eq(1)
    recession_end_dates = list(frame.index[ends])
    recession_episodes = []
    for start in frame.index[starts]:
        window_start = start - pd.DateOffset(months=lookback)
        prior_ends = [end for end in recession_end_dates if end < start]
        if prior_ends:
            window_start = max(window_start, prior_ends[-1])
        window_end = start + pd.DateOffset(months=lag_window)
        window = frame.loc[(frame.index >= window_start) & (frame.index <= window_end)]
        alerts = window.loc[window["orange_or_red"]]
        first_alert = alerts.index[0] if not alerts.empty else None
        lead_lag = None if first_alert is None else int((start.to_period("M") - first_alert.to_period("M")).n)
        recession_episodes.append({
            "recession_start": start.date().isoformat(),
            "window_start": window_start.date().isoformat(),
            "window_end": window_end.date().isoformat(),
            "first_orange_or_red": None if first_alert is None else first_alert.date().isoformat(),
            "lead_lag_months": lead_lag,
            "detected": first_alert is not None,
        })
    detected = sum(item["detected"] for item in recession_episodes)
    event_detection = {
        "unit": "NBER recession episode",
        "definition": (
            f"Detected when Orange/Red occurs from as early as {lookback} months before the recession start "
            f"through {lag_window} months after it; the window cannot cross the previous recession end."
        ),
        "episodes_eligible": len(recession_episodes),
        "episodes_detected": detected,
        "event_detection_rate": _safe_ratio(detected, len(recession_episodes)),
        "event_detection_rate_interval": exact_binomial_interval(detected, len(recession_episodes)),
        "episodes": recession_episodes,
    }

    alert_episode_analysis = _alert_episode_analysis(frame, rules)
    transitions = frame["orange_or_red"] & ~frame["orange_or_red"].shift(1, fill_value=False)
    transition_dates = [date.date().isoformat() for date in frame.index[transitions]]

    state_months = frame["overall_state"].value_counts().sort_index().to_dict()
    return {
        "ruleset_version": rules["ruleset_version"],
        "validation_type": "Current-vintage pseudo-real-time backtest",
        "coverage_start": frame.index.min().date().isoformat(),
        "coverage_end": frame.index.max().date().isoformat(),
        "months_tested": int(len(frame)),
        "monthly_horizon_classification": monthly,
        "recession_event_detection": event_detection,
        "alert_episode_analysis": alert_episode_analysis,
        "transition_diagnostics": {
            "raw_orange_or_red_transition_count": len(transition_dates),
            "raw_orange_or_red_transition_dates": transition_dates,
            "interpretation": "Transitions are state-machine diagnostics, not independent forecast events.",
        },
        "state_months": {str(k): int(v) for k, v in state_months.items()},
        "material_caveats": [
            "Historical values are the latest revised FRED observations, not the values known on each historical date.",
            "Observation dates are used as monthly anchors; exact historical release lags are not reconstructed.",
            "Monthly forecast metrics use overlapping 12-month targets and serially dependent observations; their apparent sample size overstates statistical independence.",
            "Event detection and alert-episode precision are separate tests with different denominators and must not be combined into a hit rate.",
            "Clopper-Pearson intervals quantify small-sample binomial uncertainty but do not remove dependence among business cycles.",
            "The high-yield OAS feed has limited redistributed history and is therefore supplemented by BAA10Y for long-history credit validation.",
            "Commercial real-estate delinquency is a lagging quarterly corroborator and cannot set or upgrade the credit state in this ruleset.",
            "Ruleset 0.1.1 changes only the CRE role and validation definitions; thresholds were not optimized against the revised results.",
            "A decision-grade validation requires ALFRED vintages or a sufficiently long prospectively frozen source archive.",
        ],
    }
