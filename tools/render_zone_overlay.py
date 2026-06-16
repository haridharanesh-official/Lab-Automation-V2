"""Render a zone calibration overlay from config/zones.json."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


COLORS = [
    (40, 70, 255),
    (40, 200, 255),
    (40, 220, 80),
    (255, 80, 40),
    (255, 160, 40),
    (180, 80, 255),
]
FOOT_TEST_POINTS = {
    1: (1120, 620),
    2: (650, 560),
    3: (250, 650),
    4: (1050, 150),
    5: (560, 250),
    6: (160, 300),
}


def load_zones(path: Path) -> list[np.ndarray]:
    data = json.loads(path.read_text())
    return [np.array(polygon, dtype=np.int32) for polygon in data["zones"]]


def polygon_center(polygon: np.ndarray) -> tuple[int, int]:
    moments = cv2.moments(polygon)
    if moments["m00"] == 0:
        return tuple(polygon.mean(axis=0).astype(int))
    return round(moments["m10"] / moments["m00"]), round(moments["m01"] / moments["m00"])


def render(reference: Path, zones_path: Path, output: Path) -> None:
    image = cv2.imread(str(reference))
    if image is None:
        raise FileNotFoundError(reference)
    zones = load_zones(zones_path)
    overlay = image.copy()
    for index, polygon in enumerate(zones):
        color = COLORS[index % len(COLORS)]
        cv2.fillPoly(overlay, [polygon], color)
    image = cv2.addWeighted(overlay, 0.28, image, 0.72, 0)
    for index, polygon in enumerate(zones):
        color = COLORS[index % len(COLORS)]
        cv2.polylines(image, [polygon], True, color, 4, cv2.LINE_AA)
        center = polygon_center(polygon)
        cv2.circle(image, center, 18, (0, 0, 0), -1, cv2.LINE_AA)
        cv2.putText(image, f"Z{index + 1}", (center[0] - 15, center[1] + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    for expected_zone, point in FOOT_TEST_POINTS.items():
        cv2.drawMarker(image, point, (255, 255, 255), cv2.MARKER_CROSS, 28, 3, cv2.LINE_AA)
        cv2.circle(image, point, 8, COLORS[expected_zone - 1], -1, cv2.LINE_AA)
        cv2.putText(image, f"foot Z{expected_zone}", (point[0] + 10, point[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), image):
        raise RuntimeError(f"failed to write {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", required=True)
    parser.add_argument("--zones", default="config/zones.json")
    parser.add_argument("--output", default="monitor-results/zone-calibration/zone-overlay.png")
    args = parser.parse_args()
    render(Path(args.reference), Path(args.zones), Path(args.output))
    print(args.output)


if __name__ == "__main__":
    main()
