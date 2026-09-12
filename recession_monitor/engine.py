from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from .constants import OVERALL_RANK, STATE_RANK


def _monthly_last(series: pd.Series) -> pd.Series:
    return series.sort_index().resample("ME").last()


def _monthly_frame(data: dict[str, pd.Series]) -> pd.DataFrame:
    if not data:
        return pd.DataFrame()
    monthly = pd.concat({_id: _monthly_last(s) for _id, s in data.items()}, axis=1)
    if monthly.empty:
        return monthly
    grid = pd.date_range(monthly.index.min(), monthly.index.max(), freq="ME")
    return monthly.reindex(grid).ffill()


def _state(index: pd.Index, available: pd.Series, elevated: pd.Series, severe: pd.Series) -> pd.Series:
    result = pd.Series("UNKNOWN", index=index, dtype="object")
    result.loc[available.fillna(False)] = "NORMAL"
    result.loc[(available & elevated).fillna(False)] = "ELEVATED"
    result.loc[(available & severe).fillna(False)] = "SEVERE"
    return result


def _weekly_claim_features(data: dict[str, pd.Series], rules: dict) -> pd.DataFrame:
    idx = pd.DatetimeIndex([])
    if "IC4WSA" in data:
        idx = idx.union(data["IC4WSA"].index)
    if "CCSA" in data:
        idx = idx.union(data["CCSA"].index)
    frame = pd.DataFrame(index=idx.sort_values())
    initial = data.get("IC4WSA", pd.Series(dtype=float)).reindex(frame.index).ffill()
    continued = data.get("CCSA", pd.Series(dtype=float)).reindex(frame.index).ffill()
    trailing_low = initial.rolling(52, min_periods=40).min()
    ratio = initial.div(trailing_low).sub(1.0)
    persistence = int(rules["labor"]["claims_persistence_weeks"])
    elevated = ratio.ge(float(rules["labor"]["claims_ratio_elevated"]))
    severe_level = ratio.ge(float(rules["labor"]["claims_ratio_severe"]))
    elevated_persistent = elevated.rolling(persistence, min_periods=persistence).sum().eq(persistence)
    severe_persistent = severe_level.rolling(persistence, min_periods=persistence).sum().eq(persistence)
    continuing_rising = continued.rolling(4, min_periods=4).mean().diff(4).gt(0)
    frame["claims_ratio"] = ratio
    frame["claims_elevated"] = elevated_persistent
    frame["claims_severe"] = severe_persistent & continuing_rising
    return frame.resample("ME").last()


def build_features(data: dict[str, pd.Series], rules: dict) -> pd.DataFrame:
    monthly = _monthly_frame(data)
    if monthly.empty:
        return monthly
    features = pd.DataFrame(index=monthly.index)

    # Labor
    features["sahm"] = monthly.get("SAHMREALTIME")
    features["unemployment_rate"] = monthly.get("UNRATE")
    if "UNRATE" in monthly:
        features["unemployment_rise_12m"] = monthly["UNRATE"] - monthly["UNRATE"].rolling(12, min_periods=6).min()
    features["payroll_3m_average_k"] = monthly.get("PAYEMS", pd.Series(index=monthly.index, dtype=float)).diff().rolling(3, min_periods=3).mean()
    claims = _weekly_claim_features(data, rules).reindex(monthly.index).ffill()
    features = features.join(claims, how="left")
    labor_available_count = features[["sahm", "payroll_3m_average_k", "claims_ratio"]].notna().sum(axis=1)
    labor_available = labor_available_count.ge(2)
    labor_severe = (
        features["sahm"].ge(float(rules["labor"]["sahm_severe"]))
        | (
            features["payroll_3m_average_k"].le(float(rules["labor"]["payroll_3m_average_severe_thousands"]))
            & features["claims_severe"].eq(True)
        )
    )
    labor_elevated = (
        features["sahm"].ge(float(rules["labor"]["sahm_elevated"]))
        | features["payroll_3m_average_k"].lt(float(rules["labor"]["payroll_3m_average_elevated_thousands"]))
        | features["claims_elevated"].eq(True)
    )
    features["labor_state"] = _state(features.index, labor_available, labor_elevated, labor_severe)

    # Real activity breadth
    core_ids = [sid for sid in ("W875RX1", "PCEC96", "INDPRO", "CMRMTSPL") if sid in monthly]
    core_growth = monthly[core_ids].pct_change(int(rules["activity"]["lookback_months"]), fill_method=None)
    features["activity_available_count"] = core_growth.notna().sum(axis=1)
    features["activity_contracting_count"] = (core_growth.lt(0) & core_growth.notna()).sum(axis=1)
    features["cfnai_ma3"] = monthly.get("CFNAIMA3")
    minimum = int(rules["activity"]["minimum_available_series"])
    activity_available = features["activity_available_count"].ge(minimum) | features["cfnai_ma3"].notna()
    activity_severe = (
        (features["activity_available_count"].ge(minimum)
         & features["activity_contracting_count"].ge(int(rules["activity"]["severe_contracting_series"])))
        | features["cfnai_ma3"].le(float(rules["activity"]["cfnai_severe"]))
    )
    activity_elevated = (
        (features["activity_available_count"].ge(minimum)
         & features["activity_contracting_count"].ge(int(rules["activity"]["elevated_contracting_series"])))
        | features["cfnai_ma3"].le(float(rules["activity"]["cfnai_elevated"]))
    )
    features["activity_state"] = _state(features.index, activity_available, activity_elevated, activity_severe)

    # Credit and financial stress
    daily_credit = pd.DataFrame()
    for sid in ("BAA10Y", "BAMLH0A0HYM2"):
        if sid in data:
            daily_credit[sid] = data[sid]
    if not daily_credit.empty:
        daily_credit = daily_credit.sort_index().ffill()
    baa = daily_credit.get("BAA10Y", pd.Series(dtype=float))
    hy = daily_credit.get("BAMLH0A0HYM2", pd.Series(dtype=float))
    credit_daily = pd.DataFrame(index=daily_credit.index)
    credit_daily["baa_spread"] = baa
    credit_daily["baa_20d_change"] = baa.diff(20)
    credit_daily["hy_oas"] = hy
    credit_daily["hy_20d_change"] = hy.diff(20)
    credit_monthly = credit_daily.resample("ME").last().reindex(monthly.index).ffill() if not credit_daily.empty else pd.DataFrame(index=monthly.index)
    features = features.join(credit_monthly, how="left")
    features["nfci"] = monthly.get("NFCI")
    features["stlfsi"] = monthly.get("STLFSI4")
    features["cre_delinquency"] = monthly.get("DRCRELEXFACBS")
    primary_credit_columns = ["baa_spread", "hy_oas", "nfci", "stlfsi"]
    credit_columns = primary_credit_columns + ["cre_delinquency"]
    for col in credit_columns:
        if col not in features:
            features[col] = np.nan
    # CRE delinquency is quarterly and lagging. It may corroborate primary
    # market/financial-condition stress, but cannot establish availability or
    # elevate the credit layer on its own.
    credit_available = features[primary_credit_columns].notna().sum(axis=1).ge(2)
    c = rules["credit"]
    primary_credit_severe = (
        features["baa_spread"].ge(float(c["baa_spread_severe_percent"]))
        | features["baa_20d_change"].ge(float(c["baa_20d_change_severe_percent"]))
        | features["hy_oas"].ge(float(c["high_yield_oas_severe_percent"]))
        | features["hy_20d_change"].ge(float(c["high_yield_20d_change_severe_percent"]))
        | features["nfci"].ge(float(c["nfci_severe"]))
        | features["stlfsi"].ge(float(c["stlfsi_severe"]))
    )
    primary_credit_elevated = (
        features["baa_spread"].ge(float(c["baa_spread_elevated_percent"]))
        | features["baa_20d_change"].ge(float(c["baa_20d_change_elevated_percent"]))
        | features["hy_oas"].ge(float(c["high_yield_oas_elevated_percent"]))
        | features["hy_20d_change"].ge(float(c["high_yield_20d_change_elevated_percent"]))
        | features["nfci"].ge(float(c["nfci_elevated"]))
        | features["stlfsi"].ge(float(c["stlfsi_elevated"]))
    )
    cre_elevated = features["cre_delinquency"].ge(float(c["cre_delinquency_elevated"]))
    cre_severe = features["cre_delinquency"].ge(float(c["cre_delinquency_severe"]))
    if c.get("cre_delinquency_role") != "corroboration_only":
        raise ValueError("credit.cre_delinquency_role must be corroboration_only")
    credit_elevated = primary_credit_elevated
    credit_severe = primary_credit_severe
    features["credit_primary_elevated"] = primary_credit_elevated.astype(bool)
    features["credit_primary_severe"] = primary_credit_severe.astype(bool)
    features["cre_delinquency_elevated_flag"] = cre_elevated.astype(bool)
    features["cre_delinquency_severe_flag"] = cre_severe.astype(bool)
    features["cre_corroborates_credit"] = (primary_credit_elevated & cre_elevated).astype(bool)
    features["credit_state"] = _state(features.index, credit_available, credit_elevated, credit_severe)

    # Forward warnings
    permit_yoy = monthly.get("PERMIT", pd.Series(index=monthly.index, dtype=float)).pct_change(12, fill_method=None)
    starts_yoy = monthly.get("HOUST", pd.Series(index=monthly.index, dtype=float)).pct_change(12, fill_method=None)
    features["permits_yoy"] = permit_yoy
    features["housing_starts_yoy"] = starts_yoy
    features["curve_spread"] = monthly.get("T10Y3M")
    inv_months = int(rules["forward"]["curve_inversion_persistence_months"])
    curve_inverted = features["curve_spread"].lt(0).rolling(inv_months, min_periods=inv_months).sum().eq(inv_months)
    forward_available = features[["permits_yoy", "housing_starts_yoy", "curve_spread"]].notna().any(axis=1)
    forward_severe = (
        permit_yoy.le(float(rules["forward"]["housing_yoy_severe"]))
        | starts_yoy.le(float(rules["forward"]["housing_yoy_severe"]))
    )
    forward_elevated = (
        permit_yoy.le(float(rules["forward"]["housing_yoy_elevated"]))
        | starts_yoy.le(float(rules["forward"]["housing_yoy_elevated"]))
        | curve_inverted
    )
    features["forward_state"] = _state(features.index, forward_available, forward_elevated, forward_severe)

    # Inflation / financing shock overlay
    shock_daily = pd.DataFrame()
    for sid in ("DFII10", "T10YIE"):
        if sid in data:
            shock_daily[sid] = data[sid]
    if not shock_daily.empty:
        shock_daily = shock_daily.sort_index().ffill()
    shock_metrics = pd.DataFrame(index=shock_daily.index)
    shock_metrics["real_yield_20d_change"] = shock_daily.get("DFII10", pd.Series(dtype=float)).diff(20)
    shock_metrics["breakeven_20d_change"] = shock_daily.get("T10YIE", pd.Series(dtype=float)).diff(20)
    shock_monthly = shock_metrics.resample("ME").last().reindex(monthly.index).ffill() if not shock_metrics.empty else pd.DataFrame(index=monthly.index)
    features = features.join(shock_monthly, how="left")
    oil = monthly.get("DCOILWTICO", pd.Series(index=monthly.index, dtype=float))
    features["oil_3m_change"] = oil.pct_change(3, fill_method=None)
    for col in ("real_yield_20d_change", "breakeven_20d_change"):
        if col not in features:
            features[col] = np.nan
    shock_available = features[["oil_3m_change", "real_yield_20d_change", "breakeven_20d_change"]].notna().any(axis=1)
    s = rules["shock"]
    shock_severe = (
        features["oil_3m_change"].ge(float(s["oil_3m_severe"]))
        | features["real_yield_20d_change"].ge(float(s["real_yield_20d_severe_percent"]))
        | features["breakeven_20d_change"].ge(float(s["breakeven_20d_severe_percent"]))
    )
    shock_elevated = (
        features["oil_3m_change"].ge(float(s["oil_3m_elevated"]))
        | features["real_yield_20d_change"].ge(float(s["real_yield_20d_elevated_percent"]))
        | features["breakeven_20d_change"].ge(float(s["breakeven_20d_elevated_percent"]))
    )
    features["shock_state"] = _state(features.index, shock_available, shock_elevated, shock_severe)

    features["overall_state"] = [
        overall_state(row["labor_state"], row["activity_state"], row["credit_state"], row["forward_state"], row["shock_state"], rules)
        for _, row in features.iterrows()
    ]
    return features


def overall_state(labor: str, activity: str, credit: str, forward: str, shock: str, rules: dict) -> str:
    if labor == "UNKNOWN" or activity == "UNKNOWN":
        return "UNKNOWN"
    labor_rank = STATE_RANK.get(labor, -1)
    activity_rank = STATE_RANK.get(activity, -1)
    credit_rank = STATE_RANK.get(credit, -1)
    if (labor_rank >= 2 and activity_rank >= 2) or (credit_rank >= 2 and activity_rank >= 1):
        return "RED"
    if labor_rank >= 1 and (activity_rank >= 1 or credit_rank >= 1):
        return "ORANGE"
    elevated_layers = sum(STATE_RANK.get(state, -1) >= 1 for state in (labor, activity, credit, forward, shock))
    if elevated_layers >= int(rules["overall"]["yellow_minimum_elevated_layers"]):
        return "YELLOW"
    return "GREEN"


def classify_curve(data: dict[str, pd.Series], rules: dict) -> dict[str, Any]:
    required = ("DGS10", "DGS3MO", "T10Y3M")
    if not all(sid in data and not data[sid].empty for sid in required):
        return {"pattern": "UNKNOWN"}
    frame = pd.concat({sid: data[sid] for sid in required}, axis=1).sort_index().ffill().dropna()
    if len(frame) < 21:
        return {"pattern": "UNKNOWN"}
    latest = frame.iloc[-1]
    prior = frame.iloc[-21]
    d10 = float(latest["DGS10"] - prior["DGS10"])
    d3m = float(latest["DGS3MO"] - prior["DGS3MO"])
    ds = float(latest["T10Y3M"] - prior["T10Y3M"])
    threshold = float(rules["curve"]["meaningful_20d_spread_change_percent"])
    if ds > threshold:
        if d3m < 0 and d3m < d10:
            pattern = "BULL_STEEPENER"
        elif d10 > 0 and d10 > d3m:
            pattern = "BEAR_STEEPENER"
        else:
            pattern = "MIXED_STEEPENER"
    elif ds < -threshold:
        pattern = "FLATTENING"
    else:
        pattern = "STABLE"
    return {
        "pattern": pattern,
        "observation_date": frame.index[-1].date().isoformat(),
        "spread_percent": round(float(latest["T10Y3M"]), 4),
        "change_20d_spread_percent": round(ds, 4),
        "change_20d_10y_percent": round(d10, 4),
        "change_20d_3m_percent": round(d3m, 4),
    }


def data_quality(registry: dict, metadata: dict[str, dict], as_of: date) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for sid, spec in registry["series"].items():
        meta = metadata.get(sid, {})
        last = meta.get("last_observation")
        age = (as_of - date.fromisoformat(last)).days if last else None
        max_age = int(spec["max_age_days"])
        result[sid] = {
            "status": "FRESH" if age is not None and age <= max_age else "STALE_OR_MISSING",
            "last_observation": last,
            "age_days": age,
            "max_age_days": max_age,
            "payload_sha256": meta.get("payload_sha256"),
            "release_date": None,
            "coverage_note": spec.get("coverage_note"),
            "retrieval_status": meta.get("retrieval_status"),
            "retrieval_error": meta.get("retrieval_error"),
        }
    return result


def live_snapshot(
    data: dict[str, pd.Series],
    registry: dict,
    rules: dict,
    metadata: dict[str, dict],
    as_of: date,
) -> tuple[dict[str, Any], pd.DataFrame]:
    quality = data_quality(registry, metadata, as_of)
    fresh_data = {
        sid: series
        for sid, series in data.items()
        if quality.get(sid, {}).get("status") == "FRESH" or registry["series"][sid]["layer"] == "validation"
    }
    features = build_features(fresh_data, rules)
    if features.empty:
        raise ValueError("No fresh data available for a live snapshot")
    row = features.iloc[-1]
    layers = {
        "labor": row["labor_state"],
        "activity": row["activity_state"],
        "credit": row["credit_state"],
        "forward": row["forward_state"],
        "shock": row["shock_state"],
    }
    metric_names = [
        "sahm", "unemployment_rate", "unemployment_rise_12m", "payroll_3m_average_k",
        "claims_ratio", "activity_available_count", "activity_contracting_count", "cfnai_ma3",
        "baa_spread", "baa_20d_change", "hy_oas", "hy_20d_change", "nfci", "stlfsi",
        "cre_delinquency", "credit_primary_elevated", "credit_primary_severe",
        "cre_delinquency_elevated_flag", "cre_delinquency_severe_flag", "cre_corroborates_credit",
        "permits_yoy", "housing_starts_yoy", "oil_3m_change",
        "real_yield_20d_change", "breakeven_20d_change",
    ]
    metrics = {}
    for name in metric_names:
        value = row.get(name, np.nan)
        metrics[name] = None if pd.isna(value) else round(float(value), 6)
    series_latest = {}
    for sid, series in fresh_data.items():
        if series.empty:
            continue
        series_latest[sid] = {
            "observation_date": series.index[-1].date().isoformat(),
            "value": round(float(series.iloc[-1]), 6),
        }
    snapshot = {
        "as_of": as_of.isoformat(),
        "ruleset_version": rules["ruleset_version"],
        "registry_version": registry["registry_version"],
        "overall_state": row["overall_state"],
        "overall_rank": OVERALL_RANK[row["overall_state"]],
        "layers": layers,
        "curve": classify_curve(fresh_data, rules),
        "metrics": metrics,
        "series_latest": series_latest,
        "data_quality": quality,
        "determinism": "Same raw payloads and ruleset version produce the same output.",
        "release_date_policy": "release_date remains null unless supplied by an authoritative machine-readable source.",
    }
    return snapshot, features
