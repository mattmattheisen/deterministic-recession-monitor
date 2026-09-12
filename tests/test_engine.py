from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from recession_monitor.alert import alert_decision
from recession_monitor.config import load_yaml
from recession_monitor.engine import build_features, classify_curve, overall_state
from recession_monitor.fetch import fetch_one, fetch_registry
from recession_monitor.validation import consolidate_alert_runs, exact_binomial_interval


ROOT = Path(__file__).resolve().parents[1]
RULES = load_yaml(ROOT / "config" / "rules.yaml")


class OverallStateTests(unittest.TestCase):
    def test_market_warning_alone_does_not_confirm_recession(self):
        state = overall_state("NORMAL", "NORMAL", "NORMAL", "SEVERE", "NORMAL", RULES)
        self.assertEqual(state, "GREEN")

    def test_two_warning_layers_create_yellow(self):
        state = overall_state("NORMAL", "NORMAL", "NORMAL", "ELEVATED", "ELEVATED", RULES)
        self.assertEqual(state, "YELLOW")

    def test_labor_plus_activity_create_orange(self):
        state = overall_state("ELEVATED", "ELEVATED", "NORMAL", "NORMAL", "NORMAL", RULES)
        self.assertEqual(state, "ORANGE")

    def test_severe_labor_and_activity_create_red(self):
        state = overall_state("SEVERE", "SEVERE", "NORMAL", "NORMAL", "NORMAL", RULES)
        self.assertEqual(state, "RED")

    def test_unknown_when_core_layers_missing(self):
        state = overall_state("UNKNOWN", "UNKNOWN", "SEVERE", "SEVERE", "SEVERE", RULES)
        self.assertEqual(state, "UNKNOWN")

    def test_unknown_when_activity_is_missing(self):
        state = overall_state("NORMAL", "UNKNOWN", "NORMAL", "NORMAL", "NORMAL", RULES)
        self.assertEqual(state, "UNKNOWN")


class CurveClassificationTests(unittest.TestCase):
    def _series(self, start: float, end: float) -> pd.Series:
        idx = pd.bdate_range("2026-01-01", periods=30)
        return pd.Series([start + (end - start) * i / 29 for i in range(30)], index=idx)

    def test_bull_steepener(self):
        data = {
            "DGS10": self._series(5.0, 4.7),
            "DGS3MO": self._series(5.0, 4.2),
            "T10Y3M": self._series(0.0, 0.5),
        }
        self.assertEqual(classify_curve(data, RULES)["pattern"], "BULL_STEEPENER")

    def test_bear_steepener(self):
        data = {
            "DGS10": self._series(4.0, 4.8),
            "DGS3MO": self._series(4.0, 4.2),
            "T10Y3M": self._series(0.0, 0.6),
        }
        self.assertEqual(classify_curve(data, RULES)["pattern"], "BEAR_STEEPENER")

    def test_same_inputs_same_result(self):
        data = {
            "DGS10": self._series(4.0, 4.8),
            "DGS3MO": self._series(4.0, 4.2),
            "T10Y3M": self._series(0.0, 0.6),
        }
        self.assertEqual(classify_curve(data, RULES), classify_curve(data, RULES))


class CreditCorroborationTests(unittest.TestCase):
    def _data(self, baa: float, cre: float):
        daily = pd.bdate_range("2000-01-03", periods=520)
        monthly = pd.date_range("2000-01-31", periods=24, freq="ME")
        return {
            "BAA10Y": pd.Series(baa, index=daily),
            "NFCI": pd.Series(-0.5, index=monthly),
            "STLFSI4": pd.Series(-1.0, index=monthly),
            "DRCRELEXFACBS": pd.Series(cre, index=monthly),
        }

    def test_cre_alone_cannot_elevate_credit(self):
        features = build_features(self._data(baa=2.0, cre=8.0), RULES)
        self.assertEqual(features.iloc[-1]["credit_state"], "NORMAL")
        self.assertFalse(bool(features.iloc[-1]["cre_corroborates_credit"]))

    def test_severe_cre_only_corroborates_primary_elevated_credit(self):
        features = build_features(self._data(baa=2.6, cre=8.0), RULES)
        self.assertEqual(features.iloc[-1]["credit_state"], "ELEVATED")
        self.assertTrue(bool(features.iloc[-1]["cre_corroborates_credit"]))


class ValidationDefinitionTests(unittest.TestCase):
    def test_exact_interval_for_eight_of_eight(self):
        interval = exact_binomial_interval(8, 8)
        self.assertAlmostEqual(interval["lower"], 0.6306, places=4)
        self.assertEqual(interval["upper"], 1.0)

    def test_alert_runs_are_consolidated_by_quiet_months(self):
        index = pd.date_range("2020-01-31", periods=12, freq="ME")
        active = pd.Series(
            [True, True, False, False, True, False, False, False, False, False, False, True],
            index=index,
        )
        episodes = consolidate_alert_runs(active, cooldown_months=2)
        self.assertEqual(len(episodes), 2)
        self.assertEqual(episodes[0]["raw_runs_merged"], 2)
        self.assertEqual(episodes[0]["active_months"], 3)


class VintageArchiveTests(unittest.TestCase):
    def test_vintage_payload_is_immutable(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw"
            vintage = root / "vintage"
            raw.mkdir()
            payload = b"observation_date,TEST\n2020-01-01,1.0\n"
            (raw / "TEST.csv").write_bytes(payload)
            fetch_one("TEST", "unused", "2020-01-01", raw, offline=True, vintage_dir=vintage)
            self.assertEqual((vintage / "TEST.csv").read_bytes(), payload)
            (vintage / "TEST.csv").write_bytes(b"different")
            with self.assertRaises(RuntimeError):
                fetch_one("TEST", "unused", "2020-01-01", raw, offline=True, vintage_dir=vintage)

    def test_live_timeout_can_use_labeled_cache_fallback(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw"
            raw.mkdir()
            (raw / "TEST.csv").write_bytes(b"observation_date,TEST\n2020-01-01,1.0\n")
            registry = {"base_url": "https://example.invalid", "series": {"TEST": {}}}
            with patch("recession_monitor.fetch._download", side_effect=TimeoutError("timed out")):
                data, metadata = fetch_registry(
                    registry,
                    start="2020-01-01",
                    raw_dir=raw,
                    metadata_path=root / "metadata.json",
                    workers=1,
                    download_attempts=1,
                    download_timeout=1,
                    allow_cache_fallback=True,
                )
            self.assertEqual(float(data["TEST"].iloc[-1]), 1.0)
            self.assertEqual(metadata["TEST"]["retrieval_status"], "CACHE_FALLBACK")
            self.assertIn("TimeoutError", metadata["TEST"]["retrieval_error"])


class AlertDecisionTests(unittest.TestCase):
    def _snapshot(self, overall="GREEN", labor="NORMAL", activity="NORMAL"):
        return {
            "as_of": "2026-09-12",
            "overall_state": overall,
            "layers": {"labor": labor, "activity": activity, "credit": "NORMAL", "forward": "NORMAL", "shock": "NORMAL"},
            "data_quality": {},
        }

    def test_initial_baseline_does_not_alert(self):
        self.assertFalse(alert_decision(None, self._snapshot())["required"])

    def test_overall_escalation_alerts(self):
        previous = self._snapshot("GREEN")
        current = self._snapshot("ORANGE", "ELEVATED", "ELEVATED")
        decision = alert_decision(previous, current)
        self.assertTrue(decision["required"])
        self.assertIn("overall:GREEN->ORANGE", decision["changes"])

    def test_unchanged_state_does_not_alert(self):
        snap = self._snapshot("GREEN")
        self.assertFalse(alert_decision(snap, snap)["required"])


if __name__ == "__main__":
    unittest.main()
