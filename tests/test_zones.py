from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
PATH = ROOT / "tools" / "validate_zones.py"
spec = importlib.util.spec_from_file_location("validate_zones", PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = module
spec.loader.exec_module(module)

sys.path.insert(0, str(ROOT / "ai-pc"))
from src.main import load_zones  # noqa: E402


def zone_doc(width=100, height=100):
    return {
        "version": "2.0",
        "image_width": width,
        "image_height": height,
        "camera": "labcam",
        "assignment_point": "bottom_center",
        "zones": [
            {"id": 1, "name": "Zone 1", "points": [[0, 0], [20, 0], [20, 20], [0, 20]]},
            {"id": 2, "name": "Zone 2", "points": [[30, 0], [50, 0], [50, 20], [30, 20]]},
            {"id": 3, "name": "Zone 3", "points": [[60, 0], [80, 0], [80, 20], [60, 20]]},
            {"id": 4, "name": "Zone 4", "points": [[0, 30], [20, 30], [20, 50], [0, 50]]},
            {"id": 5, "name": "Zone 5", "points": [[30, 30], [50, 30], [50, 50], [30, 50]]},
            {"id": 6, "name": "Zone 6", "points": [[60, 30], [80, 30], [80, 50], [60, 50]]},
        ],
    }


def test_loading_valid_zones_json(tmp_path):
    path = tmp_path / "zones.json"
    path.write_text(json.dumps(zone_doc()), encoding="utf-8")
    document, warnings = module.load_zone_document(path)
    assert warnings == []
    assert document["version"] == "2.0"
    assert len(document["zones"]) == 6
    assert module.validate_zone_document(document).valid


def test_missing_zones_json_does_not_crash(tmp_path):
    document, warnings = module.load_zone_document(tmp_path / "missing.json")
    assert warnings
    assert len(document["zones"]) == 6
    assert all(zone["points"] == [] for zone in document["zones"])


def test_invalid_zones_json_does_not_crash(tmp_path):
    path = tmp_path / "zones.json"
    path.write_text("{not json", encoding="utf-8")
    document, warnings = module.load_zone_document(path)
    assert warnings
    assert len(document["zones"]) == 6


def test_polygon_point_assignment_and_unknown():
    document = zone_doc()
    assert module.assign_point_to_zone((10, 10), document)["zone"] == 1
    assert module.assign_point_to_zone((90, 90), document)["status"] == "UNKNOWN"


def test_overlap_detection_warns_and_uses_lowest_zone_id():
    document = zone_doc()
    document["zones"][1]["points"] = [[10, 10], [40, 10], [40, 40], [10, 40]]
    validation = module.validate_zone_document(document)
    assert validation.valid
    assert (1, 2) in validation.overlaps
    result = module.assign_point_to_zone((15, 15), document)
    assert result["status"] == "OVERLAP"
    assert result["zone"] == 1


def test_out_of_bounds_validation_blocks_save():
    document = zone_doc()
    document["zones"][0]["points"] = [[-1, 0], [20, 0], [20, 20]]
    validation = module.validate_zone_document(document)
    assert not validation.valid
    assert any("outside" in error for error in validation.errors)


def test_save_creates_backup_before_overwrite(tmp_path):
    path = tmp_path / "zones.json"
    first = zone_doc()
    path.write_text(json.dumps(first), encoding="utf-8")
    second = zone_doc()
    second["zones"][0]["name"] = "Updated Zone 1"
    backup = module.save_zone_document(path, second)
    assert backup is not None
    assert backup.exists()
    assert json.loads(path.read_text(encoding="utf-8"))["zones"][0]["name"] == "Updated Zone 1"
    assert json.loads(backup.read_text(encoding="utf-8"))["zones"][0]["name"] == "Zone 1"


def test_exactly_six_zones_are_required():
    document = zone_doc()
    document["zones"] = document["zones"][:5]
    validation = module.validate_zone_document(document)
    assert not validation.valid
    assert "exactly six zones are required" in validation.errors


def test_bottom_center_assignment_helper():
    assert module.bottom_center_from_box([10, 20, 30, 80]) == (20, 80)


def test_runtime_load_zones_accepts_v2_object_format(tmp_path):
    path = tmp_path / "zones.json"
    path.write_text(json.dumps(zone_doc()), encoding="utf-8")
    zones = load_zones(str(path))
    assert len(zones) == 6
    assert zones[0][0] == (0, 0)
