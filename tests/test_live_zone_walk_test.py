from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path

import pytest


TOOL_PATH = Path(__file__).parents[1] / "ai-pc" / "tools" / "live_zone_walk_test.py"
spec = importlib.util.spec_from_file_location("live_zone_walk_test", TOOL_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_parse_point_accepts_integer_pair():
    assert module.parse_point("320,650") == (320, 650)
    assert module.parse_point(" 10, 20 ") == (10, 20)


def test_parse_point_rejects_bad_format():
    with pytest.raises(Exception):
        module.parse_point("320")
    with pytest.raises(Exception):
        module.parse_point("x,650")


def test_point_mode_uses_camera_perspective_zones(capsys):
    result = module.run_point_mode(Namespace(point=(260, 650), zones="config/zones.json"))
    output = capsys.readouterr().out
    assert result == 0
    assert "260,650 -> Zone 1" in output


def test_point_mode_reports_outside_zone(capsys):
    result = module.run_point_mode(Namespace(point=(480, 200), zones="config/zones.json"))
    output = capsys.readouterr().out
    assert result == 0
    assert "480,200 -> OUTSIDE_ZONE" in output


def test_observation_summary_counts_matches_and_mismatches():
    observations = [
        {"expected_zone": 1, "observed_zone": 1, "frame": 10},
        {"expected_zone": 2, "observed_zone": 3, "frame": 20},
        {"expected_zone": None, "observed_zone": None, "frame": 30},
    ]
    summary = module.summarize_observations(observations)
    assert summary["total_observations"] == 3
    assert summary["marked_observations"] == 2
    assert summary["matches"] == 1
    assert summary["mismatches"] == 1
    assert summary["mismatch_rows"] == [{"expected_zone": 2, "observed_zone": 3, "frame": 20}]


def test_build_observation_selects_expected_zone_when_present():
    row = module.build_observation(
        "expected_zone",
        frame_index=42,
        expected_zone=3,
        current_zone_counts=[0, 0, 1, 0, 0, 0],
        stable_zone_counts=[0, 0, 1, 0, 0, 0],
        assignments=[{"zone": 3, "bottom_center": (220, 420)}],
        snapshot="snapshot.jpg",
    )
    assert row["expected_zone"] == 3
    assert row["observed_zone"] == 3
    assert row["person_count"] == 1


def test_build_observation_records_mismatch_when_expected_zone_absent():
    row = module.build_observation(
        "expected_zone",
        frame_index=43,
        expected_zone=4,
        current_zone_counts=[0, 1, 0, 0, 0, 0],
        stable_zone_counts=[0, 1, 0, 0, 0, 0],
        assignments=[{"zone": 2, "bottom_center": (900, 560)}],
    )
    assert row["expected_zone"] == 4
    assert row["observed_zone"] == 2
