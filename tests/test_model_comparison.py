import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "compare_people_models.py"
spec = importlib.util.spec_from_file_location("compare_people_models", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_zone_assignment_and_summary():
    zones = [[(0, 0), (10, 0), (10, 10), (0, 10)]]
    assert module.assigned_zone((5, 5), zones) == 1
    rows = [
        {"people_count": 1, "track_ids": [1], "zone_counts": [1], "unassigned": 0, "inference_ms": 10},
        {"people_count": 1, "track_ids": [1], "zone_counts": [1], "unassigned": 0, "inference_ms": 12},
    ]
    summary = module.summarize(rows, elapsed=0.1, peak_gpu_mb=100, source_fps=30)
    assert summary["count_changes"] == 0
    assert summary["unique_track_ids"] == 1
    assert summary["class_filter"] == [0]
