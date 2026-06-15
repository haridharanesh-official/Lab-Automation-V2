import importlib.util
from pathlib import Path

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
