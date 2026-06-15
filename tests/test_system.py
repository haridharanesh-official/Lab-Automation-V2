import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load(name):
    path = ROOT / "ai-pc" / "src" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"src.{name}", path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "src"
    spec.loader.exec_module(module)
    return module


import sys
sys.path.insert(0, str(ROOT / "ai-pc"))
from src.automation import AutomationController, desired_relays
from src.main import camera_interrupted
from src.mqtt_publisher import VisionPublisher
from src.reporting import build_report, validate_report
from src.topics import assert_vision_topic_safe
from src.zones import CountWindow, assign_zone


def report(seq, zones):
    return {"version": "2.0", "sequence": seq, "timestamp": 1, "zones": zones, "total": sum(zones),
            "sample_count": 10, "window_seconds": 60, "healthy": True}


def test_median_and_polygon_assignment():
    window = CountWindow()
    for sample in ([0, 1, 2, 3, 4, 5], [2, 1, 2, 3, 4, 5], [1, 1, 2, 3, 4, 5]):
        window.add(sample)
    assert window.medians() == [1, 1, 2, 3, 4, 5]
    assert assign_zone((5, 5), [[(0, 0), (10, 0), (10, 10), (0, 10)]]) == 1


def test_invalid_duplicate_and_out_of_order_rejected():
    controller = AutomationController(mode="auto")
    assert validate_report({"zones": []}) == (False, "incomplete")
    assert controller.process(report(2, [1, 0, 0, 0, 0, 0]))["accepted"]
    assert not controller.process(report(2, [1, 0, 0, 0, 0, 0]))["accepted"]
    assert not controller.process(report(1, [1, 0, 0, 0, 0, 0]))["accepted"]


def test_modes_mapping_fans_and_deduplication():
    zones = [1, 0, 1, 0, 1, 0]
    assert desired_relays(zones) == [True, False, True, False, True, False, True, True, True, True]
    manual = AutomationController()
    monitor = AutomationController(mode="monitor")
    assert manual.process(report(1, zones))["commands"] == []
    assert monitor.process(report(1, zones))["commands"] == []
    auto = AutomationController(mode="auto")
    first = auto.process(report(1, zones))
    assert len(first["commands"]) == 7
    for command in first["commands"]:
        auto.update_confirmed(command["relay"], command["state"] == "ON")
    assert auto.process(report(2, zones))["commands"] == []


def test_two_empty_reports_and_failure_preserves_states():
    controller = AutomationController(mode="auto")
    controller.process(report(1, [1, 0, 0, 0, 0, 0]))
    controller.update_confirmed(1, True)
    controller.update_confirmed(7, True)
    assert controller.process(report(2, [0, 0, 0, 0, 0, 0]))["commands"] == []
    commands = controller.process(report(3, [0, 0, 0, 0, 0, 0]))["commands"]
    assert {c["relay"] for c in commands} == {1, 7}
    assert controller.vision_unavailable()["commands"] == []


def test_topic_safety_and_reconnect_window_clear():
    assert_vision_topic_safe("labos/v2/vision/zones/report")
    for unsafe in ("labos/v2/relay/1/set", "labos/v2/vision/relay/set", "legacy/vision/status"):
        try:
            assert_vision_topic_safe(unsafe)
            assert False
        except ValueError:
            pass
    window = CountWindow()
    window.add([1, 0, 0, 0, 0, 0])
    camera_interrupted(window)
    assert window.samples == []
    try:
        window.medians()
        assert False
    except ValueError:
        pass


def test_artifacts_enforce_namespace_and_gpio():
    ino = (ROOT / "esp32/lab_automation_v2/lab_automation_v2.ino").read_text()
    assert "{33,18,19,21,22,23,25,26,27,32}" in ino
    assert "GPIO 5" not in ino
    flow = json.loads((ROOT / "node-red/flows.json").read_text())
    assert all("labos/v2/" in node.get("topic", "labos/v2/") or node.get("topic", "") == "" for node in flow if "topic" in node)


def test_vision_publisher_rejects_unsafe_topics_before_client_publish():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def publish(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    client = FakeClient()
    publisher = VisionPublisher(client)
    publisher.publish("labos/v2/vision/status", "healthy")
    assert len(client.calls) == 1
    for unsafe in ("labos/v2/relay/1/set", "labos/v2/control/set", "labos/v2/vision/command"):
        try:
            publisher.publish(unsafe, "ON")
            assert False
        except ValueError:
            pass
    assert len(client.calls) == 1


def test_all_requested_monitor_scenarios_send_zero_commands():
    controller = AutomationController(mode="monitor")
    scenarios = [
        [1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0],
        [0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 0, 1],
        [1, 0, 1, 0, 1, 0], [1, 1, 1, 1, 1, 1], [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ]
    assert all(controller.process(report(index, zones))["commands"] == [] for index, zones in enumerate(scenarios, 1))
    assert controller.process(report(10, scenarios[-1]))["commands"] == []
    assert controller.process(report(1, scenarios[0]))["commands"] == []
    assert controller.process({"version": "2.0"})["commands"] == []
    assert controller.vision_unavailable()["commands"] == []
