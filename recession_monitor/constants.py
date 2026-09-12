from __future__ import annotations

STATE_RANK = {"UNKNOWN": -1, "NORMAL": 0, "ELEVATED": 1, "SEVERE": 2}
OVERALL_RANK = {"UNKNOWN": -1, "GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}


def max_state(*states: str) -> str:
    valid = [state for state in states if state in STATE_RANK]
    if not valid:
        return "UNKNOWN"
    return max(valid, key=STATE_RANK.get)

