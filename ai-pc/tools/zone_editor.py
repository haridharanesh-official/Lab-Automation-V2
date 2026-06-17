"""Camera-perspective polygon editor.

Zone numbers are defined in the 1280x720 camera image, not in a top-down room
diagram: Z1 bottom-left/camera-side, Z2 middle-right/lower-mid, Z3 left/mid,
Z4 top-right, Z5 upper-middle, Z6 top-left.

Controls: 1-6 select, left-click add/test, right-click undo, L load, R reset,
S save, T test point, Q quit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_zones(zones: list[list[list[int]]]) -> None:
    if len(zones) != 6 or any(len(polygon) < 3 for polygon in zones):
        raise ValueError("exactly six polygons with at least three points are required")
    import cv2
    import numpy as np
    for index, polygon in enumerate(zones):
        if abs(cv2.contourArea(np.array(polygon))) < 100:
            raise ValueError(f"zone {index + 1} has insufficient area")


def save_zones(path: str, zones: list[list[list[int]]]) -> None:
    validate_zones(zones)
    note = (
        "Camera-perspective 1280x720 calibration. Zone 1 bottom-left/camera-side, "
        "Zone 2 middle-right/lower-mid, Zone 3 left/mid working area, Zone 4 top-right, "
        "Zone 5 upper-middle, Zone 6 top-left. Approximate until supervised live click calibration passes."
    )
    Path(path).write_text(json.dumps({"note": note, "zones": zones}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--output", default="config/zones.json")
    parser.add_argument("--load", default="config/zones.json")
    args = parser.parse_args()
    import cv2

    image = cv2.imread(args.image)
    load_path = Path(args.load)
    zones = json.loads(load_path.read_text())["zones"] if load_path.exists() else [[] for _ in range(6)]
    selected = 0
    test_mode = False
    test_result = ""

    def click(event, x, y, flags, param):
        nonlocal test_result
        if event == cv2.EVENT_LBUTTONDOWN:
            if test_mode:
                from src.zones import assign_zone
                test_result = f"Point ({x},{y}) -> zone {assign_zone((x, y), zones) or 'none/overlap'}"
            else:
                zones[selected].append([x, y])
        elif event == cv2.EVENT_RBUTTONDOWN and zones[selected]:
            zones[selected].pop()

    cv2.namedWindow("zones")
    cv2.setMouseCallback("zones", click)
    while True:
        canvas = image.copy()
        for i, polygon in enumerate(zones):
            for point in polygon:
                cv2.circle(canvas, tuple(point), 4, (0, 255, 255), -1)
            if len(polygon) >= 3:
                cv2.polylines(canvas, [__import__("numpy").array(polygon)], True,
                              (0, 255, 255) if i == selected else (0, 255, 0), 2)
        cv2.putText(canvas, "Camera perspective: Z1 bottom-left, Z4 top-right, Z6 top-left",
                    (15, 25), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
        cv2.putText(canvas, f"Zone {selected + 1} | {'TEST' if test_mode else 'EDIT'} | {test_result}",
                    (15, 50), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 2)
        cv2.imshow("zones", canvas)
        key = cv2.waitKey(30) & 0xFF
        if ord("1") <= key <= ord("6"):
            selected = key - ord("1")
        elif key == ord("u") and zones[selected]:
            zones[selected].pop()
        elif key == ord("r"):
            zones = [[] for _ in range(6)]
        elif key == ord("l") and load_path.exists():
            zones = json.loads(load_path.read_text())["zones"]
        elif key == ord("s"):
            save_zones(args.output, zones)
        elif key == ord("t"):
            test_mode = not test_mode
        elif key == ord("q"):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
