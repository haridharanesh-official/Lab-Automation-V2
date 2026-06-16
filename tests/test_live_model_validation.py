import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "tools" / "live_model_validation.py"
spec = importlib.util.spec_from_file_location("live_model_validation", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_duplicate_warning_helpers():
    assert module.box_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert module.box_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    warnings = module.duplicate_warnings([[0, 0, 10, 10], [1, 1, 11, 11], [20, 20, 30, 30]], 0.65)
    assert len(warnings) == 1
    assert warnings[0]["left_index"] == 0
    assert warnings[0]["right_index"] == 1


def test_zone_assignment_is_unique():
    zones = [[(0, 0), (10, 0), (10, 10), (0, 10)], [(20, 0), (30, 0), (30, 10), (20, 10)]]
    assert module.assigned_zone((5, 5), zones) == 1
    assert module.assigned_zone((25, 5), zones) == 2
    assert module.assigned_zone((15, 5), zones) is None
