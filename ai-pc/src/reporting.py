from __future__ import annotations

import time

from .zones import CountWindow


def build_report(window: CountWindow, sequence: int, window_seconds: int = 60) -> dict:
    zones = window.medians()
    return {
        "version": "2.0",
        "sequence": sequence,
        "timestamp": int(time.time()),
        "zones": zones,
        "total": sum(zones),
        "sample_count": len(window.samples),
        "window_seconds": window_seconds,
        "healthy": True,
    }


def validate_report(report: dict) -> tuple[bool, str]:
    required = {"version", "sequence", "timestamp", "zones", "total", "sample_count", "window_seconds", "healthy"}
    if not isinstance(report, dict) or not required.issubset(report):
        return False, "incomplete"
    zones = report["zones"]
    if report["version"] != "2.0" or report["healthy"] is not True:
        return False, "unhealthy"
    if not isinstance(report["sequence"], int) or report["sequence"] < 0:
        return False, "invalid sequence"
    if not isinstance(zones, list) or len(zones) != 6:
        return False, "invalid zones"
    if any(not isinstance(value, int) or value < 0 for value in zones):
        return False, "invalid counts"
    if report["total"] != sum(zones) or report["sample_count"] <= 0 or report["window_seconds"] != 60:
        return False, "invalid metadata"
    return True, "ok"

