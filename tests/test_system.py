import importlib.util
import json
from datetime import datetime
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
from src.automation import (
    AutomationController,
    PrioritySafetyController,
    desired_relays,
    desired_lab_relays_for_stage,
    is_within_fallback_window,
)
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
    assert_vision_topic_safe("lab/vision/people_count")
    assert_vision_topic_safe("lab/vision/source_status")
    for unsafe in ("lab/control/relay1/set", "lab/vision/relay/set", "legacy/vision/status"):
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
    assert "homeassistant/switch/" in ino
    flow = json.loads((ROOT / "node-red/flows.json").read_text())
    assert all("lab/" in node.get("topic", "lab/") or node.get("topic", "") == "" for node in flow if "topic" in node)
    fn_node = next(node for node in flow if node.get("type") == "function" and node.get("name") == "Priority Safety Controller")
    func = fn_node["func"]
    assert "manual_override/clear" in json.dumps(flow)
    assert "TIMETABLE_FALLBACK" in func
    assert "manualOverrides" in func
    assert "priority_state" in func
    assert "8*60+30" in func and "13*60" in func
    assert "topic==='lab/automation/mode'" in func
    assert "String(msg.payload).trim().toLowerCase()" in func
    assert "['manual','monitor','auto'].includes(next)" in func
    assert "diagnostics.push(m('lab/automation/mode_state',value,true))" in func


def test_vision_publisher_rejects_unsafe_topics_before_client_publish():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def publish(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    client = FakeClient()
    publisher = VisionPublisher(client)
    publisher.publish("lab/vision/status", "healthy")
    assert len(client.calls) == 1
    for unsafe in ("lab/control/relay/1/set", "lab/control/set", "lab/vision/command"):
        try:
            publisher.publish(unsafe, "ON")
            assert False
        except ValueError:
            pass
    assert len(client.calls) == 1


def test_vision_publisher_serializes_live_people_count_payload():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def publish(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    payload = {
        "publisher": "labvision-ai-pc",
        "timestamp": 1234567890,
        "total_count": 2,
        "stable_count": 2,
        "zone_counts": [1, 1, 0, 0, 0, 0],
        "source_healthy": True,
        "status": "online",
    }
    client = FakeClient()
    VisionPublisher(client).publish("lab/vision/people_count", payload)
    assert len(client.calls) == 1
    args, kwargs = client.calls[0]
    assert args[0] == "lab/vision/people_count"
    assert json.loads(args[1]) == payload
    assert kwargs["qos"] == 1


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


def test_priority_controller_manual_override_wins():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 16, 9, 0, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.last_count_ms = now_ms
    controller.last_known_automation = desired_lab_relays_for_stage("TWO_THREE")
    controller.manual_overrides[2] = "OFF"
    payload = {
        "timestamp": now_ms,
        "stable_count": 4,
        "source_healthy": True,
        "status": "online",
    }
    result = controller.process_people_count(payload, now)
    assert result["wanted"][2] == "OFF"


def test_priority_controller_timetable_fallback_inside_window():
    controller = PrioritySafetyController(mode="auto")
    controller.mark_service_status("offline")
    controller.mark_source_status("unhealthy")
    now = datetime(2026, 6, 16, 9, 0, 0)
    result = controller.process_people_count({}, now)
    assert result["stage"] == "TIMETABLE_FALLBACK"
    assert result["wanted"] == desired_lab_relays_for_stage("FOUR_PLUS")


def test_priority_controller_outside_window_delays_off():
    controller = PrioritySafetyController(mode="auto")
    controller.last_known_automation = desired_lab_relays_for_stage("ONE")
    controller.mark_service_status("offline")
    controller.mark_source_status("unhealthy")
    first = controller.process_people_count({}, datetime(2026, 6, 16, 18, 0, 0))
    assert first["stage"] == "TIMETABLE_HOLD"
    controller.fallback_off_since_ms -= controller.outside_window_off_delay_ms + 1
    second = controller.process_people_count({}, datetime(2026, 6, 16, 18, 10, 0))
    assert second["stage"] == "TIMETABLE_OFF"


def test_priority_controller_healthy_people_count_drives_automation():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 16, 9, 5, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    payload = {
        "timestamp": now_ms,
        "stable_count": 2,
        "source_healthy": True,
        "status": "online",
    }
    first = controller.process_people_count(payload, now)
    second = controller.process_people_count(payload, now)
    controller.last_apply_ms -= controller.min_change_ms + 1
    third = controller.process_people_count(payload, now)
    assert first["stage"] == "STABILIZING"
    assert second["stage"] == "STABILIZING"
    assert third["stage"] == "TWO_THREE"


def test_fallback_window_helper():
    assert is_within_fallback_window(datetime(2026, 6, 16, 8, 30))
    assert is_within_fallback_window(datetime(2026, 6, 16, 13, 15))
    assert not is_within_fallback_window(datetime(2026, 6, 16, 12, 45))
