from __future__ import annotations

import argparse
import json
import time

from src.automation import AutomationController

SCENARIOS = [
    ("zone_1", 1, [1, 0, 0, 0, 0, 0]),
    ("zone_2", 2, [0, 1, 0, 0, 0, 0]),
    ("zone_3", 3, [0, 0, 1, 0, 0, 0]),
    ("zone_4", 4, [0, 0, 0, 1, 0, 0]),
    ("zone_5", 5, [0, 0, 0, 0, 1, 0]),
    ("zone_6", 6, [0, 0, 0, 0, 0, 1]),
    ("multiple", 7, [1, 1, 0, 0, 1, 0]),
    ("all_occupied", 8, [1, 1, 1, 1, 1, 1]),
    ("empty_first", 9, [0, 0, 0, 0, 0, 0]),
    ("empty_second", 10, [0, 0, 0, 0, 0, 0]),
]


def reports():
    for name, sequence, zones in SCENARIOS:
        yield name, {"version": "2.0", "sequence": sequence, "timestamp": int(time.time()), "zones": zones,
                     "total": sum(zones), "sample_count": 1200, "window_seconds": 60, "healthy": True}
    yield "invalid", {"version": "2.0", "sequence": 11, "zones": [1]}
    yield "duplicate", next(report for name, report in reports() if name == "empty_second")
    out_of_order = next(report for name, report in reports() if name == "zone_1")
    yield "out_of_order", out_of_order


def main():
    parser = argparse.ArgumentParser(description="Print safe vision reports; add MQTT publishing only in a supervised environment.")
    parser.parse_args()
    controller = AutomationController(mode="monitor")
    relay_commands = 0
    for name, report in reports():
        result = controller.process(report)
        relay_commands += len(result["commands"])
        print(json.dumps({"scenario": name, "result": result}))
    unavailable = controller.vision_unavailable()
    relay_commands += len(unavailable["commands"])
    print(json.dumps({"scenario": "vision_unavailable", "result": unavailable}))
    print(json.dumps({"mode": controller.mode, "relay_set_commands": relay_commands}))


if __name__ == "__main__":
    main()
