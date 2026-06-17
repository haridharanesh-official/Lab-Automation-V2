import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np

PATH = Path(__file__).parents[1] / "tools" / "validate_zone_geometry.py"
spec = importlib.util.spec_from_file_location("validate_zone_geometry", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_centres_unique_and_shared_boundaries_are_reported():
    zones = [
        [[0, 0], [10, 0], [10, 10], [0, 10]],
        [[10, 0], [20, 0], [20, 10], [10, 10]],
    ]
    result = module.validate(zones)
    assert result["all_centres_unique"]
    assert result["overlap_points"] > 0


def load_config_zones():
    return json.loads((Path(__file__).parents[1] / "config" / "zones.json").read_text())["zones"]


def classify(point, zones):
    return [
        index + 1
        for index, polygon in enumerate(zones)
        if cv2.pointPolygonTest(np.array(polygon), point, False) >= 0
    ]


def near_boundary(point, zones, margin=12):
    return any(
        abs(cv2.pointPolygonTest(np.array(polygon), point, True)) <= margin
        for polygon in zones
    )


def test_six_perspective_polygons_load():
    zones = load_config_zones()
    assert len(zones) == 6
    assert all(len(polygon) >= 4 for polygon in zones)


def test_camera_perspective_zone_numbering():
    zones = load_config_zones()
    points = {
        1: (260, 650),   # bottom-left / camera-side
        2: (900, 560),   # middle-right / lower-mid
        3: (220, 420),   # left/mid working area
        4: (1050, 160),  # top-right
        5: (620, 160),   # upper-middle
        6: (160, 150),   # top-left
    }
    for expected_zone, point in points.items():
        assert classify(point, zones) == [expected_zone]


def test_boundary_margin_uncertainty():
    zones = load_config_zones()
    assert near_boundary((430, 470), zones)
    assert not near_boundary((260, 650), zones)


def test_no_accidental_interior_overlaps():
    zones = load_config_zones()
    for y in range(20, 700, 40):
        for x in range(20, 1260, 40):
            matches = [
                index + 1
                for index, polygon in enumerate(zones)
                if cv2.pointPolygonTest(np.array(polygon), (x, y), False) > 0
            ]
            assert len(matches) <= 1
