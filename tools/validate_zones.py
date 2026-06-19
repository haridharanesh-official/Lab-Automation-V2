"""Validate and save six-zone camera calibration files.

This module is calibration-only. It does not publish MQTT, change modes, or
control relays.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ZONE_COUNT = 6
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720


Point = tuple[int, int]
Polygon = list[Point]


@dataclass
class ZoneValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    overlaps: list[tuple[int, int]] = field(default_factory=list)


def empty_zone_document(width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> dict[str, Any]:
    return {
        "version": "2.0",
        "image_width": int(width),
        "image_height": int(height),
        "camera": "labcam",
        "assignment_point": "bottom_center",
        "zones": [
            {"id": zone_id, "name": f"Zone {zone_id}", "points": []}
            for zone_id in range(1, ZONE_COUNT + 1)
        ],
    }


def bottom_center_from_box(box: list[int] | tuple[int, int, int, int]) -> Point:
    if len(box) != 4:
        raise ValueError("box must be [x1, y1, x2, y2]")
    return (int((box[0] + box[2]) // 2), int(box[3]))


def normalize_zone_document(data: Any, width: int | None = None, height: int | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("zones file must contain a JSON object")
    raw_zones = data.get("zones", [])
    image_width = int(data.get("image_width") or width or DEFAULT_WIDTH)
    image_height = int(data.get("image_height") or height or DEFAULT_HEIGHT)
    zones: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for index, raw_zone in enumerate(raw_zones):
        if isinstance(raw_zone, dict):
            zone_id = int(raw_zone.get("id", index + 1))
            name = str(raw_zone.get("name") or f"Zone {zone_id}")
            raw_points = raw_zone.get("points", [])
        else:
            zone_id = index + 1
            name = f"Zone {zone_id}"
            raw_points = raw_zone
        if zone_id in seen_ids:
            raise ValueError(f"duplicate zone id {zone_id}")
        seen_ids.add(zone_id)
        points: list[list[int]] = []
        for point in raw_points or []:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError(f"zone {zone_id} contains an invalid point")
            points.append([int(round(float(point[0]))), int(round(float(point[1])))])
        zones.append({"id": zone_id, "name": name, "points": points})
    return {
        "version": "2.0",
        "image_width": image_width,
        "image_height": image_height,
        "camera": str(data.get("camera") or "labcam"),
        "assignment_point": str(data.get("assignment_point") or "bottom_center"),
        "zones": sorted(zones, key=lambda zone: zone["id"]),
    }


def load_zone_document(path: str | Path, width: int | None = None, height: int | None = None) -> tuple[dict[str, Any], list[str]]:
    zone_path = Path(path)
    warnings: list[str] = []
    if not zone_path.exists():
        warnings.append(f"{zone_path} does not exist; starting with empty zones")
        return empty_zone_document(width or DEFAULT_WIDTH, height or DEFAULT_HEIGHT), warnings
    try:
        data = json.loads(zone_path.read_text(encoding="utf-8"))
        return normalize_zone_document(data, width, height), warnings
    except Exception as exc:
        warnings.append(f"could not load {zone_path}: {exc}; starting with empty zones")
        return empty_zone_document(width or DEFAULT_WIDTH, height or DEFAULT_HEIGHT), warnings


def polygons_from_document(document: dict[str, Any]) -> list[Polygon]:
    polygons: list[Polygon] = []
    for zone in document.get("zones", []):
        polygons.append([(int(point[0]), int(point[1])) for point in zone.get("points", [])])
    return polygons


def assign_point_to_zone(point: Point, document_or_polygons: dict[str, Any] | list[Polygon]) -> dict[str, Any]:
    polygons = (
        polygons_from_document(document_or_polygons)
        if isinstance(document_or_polygons, dict)
        else document_or_polygons
    )
    matches = [
        index + 1
        for index, polygon in enumerate(polygons)
        if len(polygon) >= 3 and cv2.pointPolygonTest(np.array(polygon, dtype=np.int32), point, False) >= 0
    ]
    return {
        "zone": min(matches) if matches else None,
        "matches": matches,
        "status": "UNKNOWN" if not matches else ("OVERLAP" if len(matches) > 1 else "OK"),
    }


def detect_overlaps(polygons: list[Polygon], width: int, height: int) -> list[tuple[int, int]]:
    masks: list[np.ndarray | None] = []
    for polygon in polygons:
        if len(polygon) < 3:
            masks.append(None)
            continue
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [np.array(polygon, dtype=np.int32)], 255)
        masks.append(mask)
    overlaps: list[tuple[int, int]] = []
    for left in range(len(masks)):
        for right in range(left + 1, len(masks)):
            if masks[left] is None or masks[right] is None:
                continue
            if cv2.countNonZero(cv2.bitwise_and(masks[left], masks[right])) > 0:
                overlaps.append((left + 1, right + 1))
    return overlaps


def estimate_unmapped_fraction(polygons: list[Polygon], width: int, height: int) -> float:
    if width <= 0 or height <= 0:
        return 1.0
    mask = np.zeros((height, width), dtype=np.uint8)
    for polygon in polygons:
        if len(polygon) >= 3:
            cv2.fillPoly(mask, [np.array(polygon, dtype=np.int32)], 255)
    mapped = cv2.countNonZero(mask)
    return 1.0 - (mapped / float(width * height))


def validate_zone_document(document: dict[str, Any]) -> ZoneValidation:
    errors: list[str] = []
    warnings: list[str] = []
    zones = document.get("zones", [])
    width = int(document.get("image_width") or 0)
    height = int(document.get("image_height") or 0)
    if width <= 0 or height <= 0:
        errors.append("image_width and image_height must be positive")
    if len(zones) != ZONE_COUNT:
        errors.append("exactly six zones are required")
    ids = [zone.get("id") for zone in zones if isinstance(zone, dict)]
    if len(ids) != len(set(ids)):
        errors.append("duplicate zone IDs are not allowed")
    if set(ids) != set(range(1, ZONE_COUNT + 1)):
        errors.append("zone IDs must be exactly 1 through 6")

    polygons = polygons_from_document(document)
    for index, polygon in enumerate(polygons, 1):
        if len(polygon) < 3:
            errors.append(f"zone {index} must have at least 3 points")
        for x, y in polygon:
            if x < 0 or y < 0 or x > width or y > height:
                errors.append(f"zone {index} point ({x}, {y}) is outside {width}x{height}")
    overlaps = detect_overlaps(polygons, width, height) if width > 0 and height > 0 else []
    for left, right in overlaps:
        warnings.append(f"zone {left} overlaps zone {right}")
    unmapped_fraction = estimate_unmapped_fraction(polygons, width, height) if width > 0 and height > 0 else 1.0
    if unmapped_fraction > 0.25:
        warnings.append(f"large unmapped image area: {unmapped_fraction:.0%}")
    return ZoneValidation(valid=not errors, errors=errors, warnings=warnings, overlaps=overlaps)


def create_backup(path: str | Path) -> Path | None:
    zone_path = Path(path)
    if not zone_path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = zone_path.with_name(f"{zone_path.stem}.backup-{stamp}{zone_path.suffix}")
    backup.write_bytes(zone_path.read_bytes())
    return backup


def save_zone_document(path: str | Path, document: dict[str, Any]) -> Path | None:
    normalized = normalize_zone_document(document)
    validation = validate_zone_document(normalized)
    if not validation.valid:
        raise ValueError("; ".join(validation.errors))
    zone_path = Path(path)
    zone_path.parent.mkdir(parents=True, exist_ok=True)
    backup = create_backup(zone_path)
    zone_path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Lab Automation zone polygons.")
    parser.add_argument("zones_path", nargs="?")
    parser.add_argument("--zones", default="config/zones.json")
    parser.add_argument("--point", nargs=2, type=int, metavar=("X", "Y"))
    args = parser.parse_args()
    zones_path = args.zones_path or args.zones
    document, warnings = load_zone_document(zones_path)
    validation = validate_zone_document(document)
    for warning in warnings + validation.warnings:
        print(f"WARNING: {warning}")
    if args.point:
        result = assign_point_to_zone((args.point[0], args.point[1]), document)
        print(json.dumps(result, indent=2))
    if validation.errors:
        for error in validation.errors:
            print(f"ERROR: {error}")
        return 1
    print("zones valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
