from __future__ import annotations

from typing import Any

from .constants import OVERALL_RANK, STATE_RANK


def alert_decision(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if previous is None:
        return {"required": False, "reason": "INITIAL_BASELINE", "changes": []}
    changes: list[str] = []
    previous_overall = previous.get("overall_state", "UNKNOWN")
    current_overall = current.get("overall_state", "UNKNOWN")
    if OVERALL_RANK.get(current_overall, -1) > OVERALL_RANK.get(previous_overall, -1):
        changes.append(f"overall:{previous_overall}->{current_overall}")
    previous_layers = previous.get("layers", {})
    for layer, state in current.get("layers", {}).items():
        prior = previous_layers.get(layer, "UNKNOWN")
        if STATE_RANK.get(state, -1) > STATE_RANK.get(prior, -1) and state == "SEVERE":
            changes.append(f"{layer}:{prior}->{state}")
    core_series = {"SAHMREALTIME", "UNRATE", "PAYEMS", "IC4WSA", "W875RX1", "INDPRO", "CFNAIMA3"}
    previous_quality = previous.get("data_quality", {})
    current_quality = current.get("data_quality", {})
    for sid in sorted(core_series):
        old = previous_quality.get(sid, {}).get("status")
        new = current_quality.get(sid, {}).get("status")
        if old == "FRESH" and new == "STALE_OR_MISSING":
            changes.append(f"data_quality:{sid}:STALE_OR_MISSING")
    return {
        "required": bool(changes),
        "reason": "MATERIAL_ESCALATION" if changes else "NO_MATERIAL_ESCALATION",
        "changes": changes,
        "previous_as_of": previous.get("as_of"),
        "previous_overall_state": previous_overall,
    }

