import importlib.util
from pathlib import Path

PATH = Path(__file__).parents[1] / "tools" / "live_monitor_validation.py"
spec = importlib.util.spec_from_file_location("live_monitor_validation", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_live_monitor_refuses_non_monitor_mode(tmp_path):
    config = {"mode": "auto", "camera": {}, "model": {}}
    try:
        module.run(config, 0, tmp_path / "summary.json", False)
        assert False
    except ValueError:
        pass
