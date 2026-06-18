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
from src.main import (
    DebouncedPeopleCount,
    bottom_center_point,
    frame_assignments,
    load_zones,
    normalize_counting_mode,
    publish_status,
    render_display_frame,
    total_people_assignments,
)
from src.mqtt_publisher import VisionPublisher
from src.reporting import build_report, validate_report
from src.topics import assert_vision_topic_safe
from src.zones import CountWindow, assign_zone


def report(seq, zones):
    return {"version": "2.0", "sequence": seq, "timestamp": 1, "zones": zones, "total": sum(zones),
            "sample_count": 10, "window_seconds": 60, "healthy": True}


class FakeTensor:
    def __init__(self, values):
        self.values = values

    def int(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self.values


def test_median_and_polygon_assignment():
    window = CountWindow()
    for sample in ([0, 1, 2, 3, 4, 5], [2, 1, 2, 3, 4, 5], [1, 1, 2, 3, 4, 5]):
        window.add(sample, sample_time=len(window.samples))
    assert window.medians(now=2) == [1, 1, 2, 3, 4, 5]
    assert window.current_counts() == [1, 1, 2, 3, 4, 5]
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
    assert "manualOverrides" in func
    assert "priority_state" in func
    assert "topic==='lab/automation/mode'" in func
    assert "String(msg.payload).trim().toLowerCase()" in func
    assert "['manual','monitor','auto'].includes(next)" in func
    assert "diagnostics.push(m('lab/automation/mode_state',value,true))" in func
    assert "decisionSource:'PEOPLE_COUNT'" in func
    assert "decisionSource:'VISION_STALE'" in func
    assert "hasManualOverrides()" in func
    assert "decision_source:target.decisionSource" in func


def test_home_assistant_mqtt_contract_matches_lab_runtime():
    mqtt_yaml = (ROOT / "home-assistant/mqtt.yaml").read_text()
    assert "command_topic: lab/automation/mode" in mqtt_yaml
    assert "state_topic: lab/automation/mode_state" in mqtt_yaml
    assert "options: [manual, monitor, auto]" in mqtt_yaml
    assert "state_topic: lab/vision/status" in mqtt_yaml
    assert "state_topic: lab/vision/source_status" in mqtt_yaml
    assert "state_topic: lab/automation/priority_state" in mqtt_yaml
    assert "state_topic: lab/vision/people_count" in mqtt_yaml
    assert "state_topic: lab/vision/raw_people_count" in mqtt_yaml
    assert "unique_id: lab_vision_raw_people_count" in mqtt_yaml
    assert "command_topic: lab/control/relay1/set" in mqtt_yaml
    assert "state_topic: lab/control/relay10/state" in mqtt_yaml
    assert "labos/v2/" not in mqtt_yaml


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


def test_publish_status_splits_raw_and_debounced_people_count_topics():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def publish(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    client = FakeClient()
    publish_status(
        VisionPublisher(client),
        "healthy",
        stable_count=2,
        stable_zone_counts=[1, 1, 0, 0, 0, 0],
        current_zone_counts=[2, 0, 0, 0, 0, 0],
        debounced_zone_counts=[1, 0, 0, 0, 0, 0],
        frame_fps=24.5,
        latency_ms=35.2,
    )
    by_topic = {args[0]: json.loads(args[1]) if args[0].startswith("lab/vision/") and args[1].startswith("{") else args[1]
                for args, _kwargs in client.calls}
    assert by_topic["lab/vision/raw_people_count"]["raw_total_count"] == 2
    assert by_topic["lab/vision/raw_people_count"]["raw_zone_counts"] == [2, 0, 0, 0, 0, 0]
    stable_payload = by_topic["lab/vision/people_count"]
    assert stable_payload["stable_count"] == 1
    assert stable_payload["zone_counts"] == [1, 0, 0, 0, 0, 0]
    assert stable_payload["window_stable_count"] == 2
    assert stable_payload["raw_total_count"] == 2


def test_publish_status_total_count_mode_omits_zone_payloads():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def publish(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    client = FakeClient()
    publish_status(
        VisionPublisher(client),
        "healthy",
        stable_count=3,
        stable_zone_counts=[3, 0, 0, 0, 0, 0],
        current_zone_counts=[4, 0, 0, 0, 0, 0],
        debounced_zone_counts=[3, 0, 0, 0, 0, 0],
        frame_fps=25.0,
        latency_ms=12.0,
        counting_mode="total-count",
    )
    by_topic = {args[0]: json.loads(args[1]) if args[1].startswith("{") else args[1] for args, _kwargs in client.calls}
    assert by_topic["lab/vision/raw_people_count"]["counting_mode"] == "total-count"
    assert by_topic["lab/vision/raw_people_count"]["raw_total_count"] == 4
    assert by_topic["lab/vision/raw_people_count"]["raw_zone_counts"] is None
    stable_payload = by_topic["lab/vision/people_count"]
    assert stable_payload["counting_mode"] == "total-count"
    assert stable_payload["stable_count"] == 3
    assert stable_payload["zone_counts"] is None
    assert stable_payload["window_zone_counts"] is None
    assert stable_payload["raw_zone_counts"] is None


def test_publish_status_zone_count_mode_keeps_zone_payloads():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def publish(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    client = FakeClient()
    publish_status(
        VisionPublisher(client),
        "healthy",
        stable_count=3,
        stable_zone_counts=[1, 2, 0, 0, 0, 0],
        current_zone_counts=[1, 1, 1, 0, 0, 0],
        debounced_zone_counts=[1, 2, 0, 0, 0, 0],
        frame_fps=25.0,
        latency_ms=12.0,
        counting_mode="zone-count",
    )
    by_topic = {args[0]: json.loads(args[1]) if args[1].startswith("{") else args[1] for args, _kwargs in client.calls}
    assert by_topic["lab/vision/people_count"]["counting_mode"] == "zone-count"
    assert by_topic["lab/vision/people_count"]["zone_counts"] == [1, 2, 0, 0, 0, 0]
    assert by_topic["lab/vision/raw_people_count"]["raw_zone_counts"] == [1, 1, 1, 0, 0, 0]


def test_counting_mode_validation():
    assert normalize_counting_mode(None) == "total-count"
    assert normalize_counting_mode("ZONE-COUNT") == "zone-count"
    try:
        normalize_counting_mode("zones")
        assert False
    except ValueError:
        pass


def test_debounced_people_count_prevents_fast_zero_two_flicker():
    debouncer = DebouncedPeopleCount(stable_seconds=2, zero_hold_seconds=6)
    assert debouncer.update([0, 0, 0, 0, 0, 0], 0, True) == [0, 0, 0, 0, 0, 0]
    assert debouncer.update([2, 0, 0, 0, 0, 0], 1, True) == [0, 0, 0, 0, 0, 0]
    assert debouncer.update([0, 0, 0, 0, 0, 0], 1.5, True) == [0, 0, 0, 0, 0, 0]
    assert debouncer.update([2, 0, 0, 0, 0, 0], 2, True) == [0, 0, 0, 0, 0, 0]
    assert debouncer.update([2, 0, 0, 0, 0, 0], 4.1, True) == [2, 0, 0, 0, 0, 0]


def test_debounced_people_count_holds_last_good_count_through_misses_and_camera_failure():
    debouncer = DebouncedPeopleCount(stable_seconds=1, zero_hold_seconds=5)
    debouncer.update([2, 0, 0, 0, 0, 0], 0, True)
    assert debouncer.update([2, 0, 0, 0, 0, 0], 1.2, True) == [2, 0, 0, 0, 0, 0]
    assert debouncer.update([0, 0, 0, 0, 0, 0], 2, True) == [2, 0, 0, 0, 0, 0]
    assert debouncer.update([0, 0, 0, 0, 0, 0], 6.5, False) == [2, 0, 0, 0, 0, 0]
    assert debouncer.update([0, 0, 0, 0, 0, 0], 8, True) == [2, 0, 0, 0, 0, 0]
    assert debouncer.update([0, 0, 0, 0, 0, 0], 13.1, True) == [0, 0, 0, 0, 0, 0]


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
    assert result["stage"] == "VISION_STALE"
    assert result["commands"] == []


def test_priority_controller_outside_window_delays_off():
    controller = PrioritySafetyController(mode="auto")
    controller.last_known_automation = desired_lab_relays_for_stage("ONE")
    controller.mark_service_status("offline")
    controller.mark_source_status("unhealthy")
    first = controller.process_people_count({}, datetime(2026, 6, 16, 18, 0, 0))
    assert first["stage"] == "VISION_STALE"
    second = controller.process_people_count({}, datetime(2026, 6, 16, 18, 10, 0))
    assert second["stage"] == "VISION_STALE"
    assert second["commands"] == []


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


def test_people_count_auto_stage_relay_rules_ignore_zone_counts():
    controller = PrioritySafetyController(mode="auto")
    controller.stable_reads_required = 1
    controller.min_change_ms = 0
    now = datetime(2026, 6, 16, 9, 5, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)

    cases = [
        (0, "ZERO_HOLD", desired_lab_relays_for_stage("EMPTY")),
        (1, "ONE", desired_lab_relays_for_stage("ONE")),
        (2, "TWO_THREE", desired_lab_relays_for_stage("TWO_THREE")),
        (3, "TWO_THREE", desired_lab_relays_for_stage("TWO_THREE")),
        (4, "FOUR_PLUS", desired_lab_relays_for_stage("FOUR_PLUS")),
        (8, "FOUR_PLUS", desired_lab_relays_for_stage("FOUR_PLUS")),
    ]
    for index, (count, expected_stage, expected_relays) in enumerate(cases):
        payload = {
            "timestamp": now_ms + index,
            "stable_count": count,
            "total_count": count,
            "zone_counts": [0, 99, 0, 99, 0, 99],
            "source_healthy": True,
            "status": "online",
        }
        result = controller.process_people_count(payload, datetime.fromtimestamp((now_ms + index) / 1000))
        assert result["stage"] == expected_stage
        assert result["wanted"] == expected_relays


def test_people_count_stage_relay_mapping_matches_current_auto_contract():
    assert desired_lab_relays_for_stage("EMPTY") == {
        2: "OFF", 3: "OFF", 4: "OFF", 6: "OFF", 7: "OFF", 8: "OFF"
    }
    assert desired_lab_relays_for_stage("ONE") == {
        2: "ON", 3: "OFF", 4: "OFF", 6: "OFF", 7: "ON", 8: "OFF"
    }
    assert desired_lab_relays_for_stage("TWO_THREE") == {
        2: "ON", 3: "ON", 4: "OFF", 6: "ON", 7: "ON", 8: "OFF"
    }
    assert desired_lab_relays_for_stage("FOUR_PLUS") == {
        2: "ON", 3: "ON", 4: "ON", 6: "ON", 7: "ON", 8: "ON"
    }


def test_priority_controller_auto_stale_vision_keeps_mode_and_uses_fallback():
    controller = PrioritySafetyController(mode="auto")
    controller.mark_service_status("offline")
    controller.mark_source_status("unhealthy")
    now = datetime(2026, 6, 16, 9, 0, 0)
    result = controller.process_people_count({}, now)
    assert controller.mode == "auto"
    assert result["stage"] == "VISION_STALE"
    assert result["commands"] == []


def test_priority_controller_manual_and_monitor_stale_emit_no_commands():
    manual = PrioritySafetyController(mode="manual")
    manual.mark_service_status("offline")
    manual.mark_source_status("unhealthy")
    monitor = PrioritySafetyController(mode="monitor")
    monitor.mark_service_status("offline")
    monitor.mark_source_status("unhealthy")
    now = datetime(2026, 6, 16, 18, 0, 0)
    manual_result = manual.process_people_count({}, now)
    monitor_result = monitor.process_people_count({}, now)
    assert manual.mode == "manual"
    assert monitor.mode == "monitor"
    assert manual_result["commands"] == []
    assert monitor_result["commands"] == []


def test_priority_controller_relay_reconnect_resyncs_unchanged_auto_count():
    controller = PrioritySafetyController(mode="auto")
    controller.stable_reads_required = 1
    controller.min_change_ms = 0
    now = datetime(2026, 6, 16, 9, 5, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    payload = {
        "timestamp": now_ms,
        "stable_count": 7,
        "source_healthy": True,
        "status": "online",
    }
    first = controller.process_people_count(payload, now)
    assert first["stage"] == "FOUR_PLUS"
    assert first["commands"]
    for relay in (2, 3, 4, 6, 7, 8):
        controller.update_confirmed(relay, "ON")
    controller.last_commanded = {relay: "ON" for relay in (2, 3, 4, 6, 7, 8)}

    offline = controller.mark_relay_status("offline")
    assert offline["commands"] == []
    assert controller.confirmed == {}
    assert controller.last_commanded == {}

    reconnect = controller.mark_relay_status("online", now)
    assert reconnect["stage"] == "FOUR_PLUS"
    assert {command["relay"] for command in reconnect["commands"]} == {2, 3, 4, 6, 7, 8}
    assert all(command["state"] == "ON" for command in reconnect["commands"])

    repeated = controller.mark_relay_status("online", now)
    assert repeated["commands"] == []


def test_priority_controller_entering_auto_recalculates_latest_count_immediately():
    controller = PrioritySafetyController(mode="manual")
    now = datetime(2026, 6, 18, 10, 0, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.latest_count = 3
    controller.last_count_ms = now_ms
    controller.confirmed = {2: "OFF", 3: "OFF", 4: "OFF", 6: "OFF", 7: "OFF", 8: "OFF"}
    controller.last_commanded = {2: "ON", 3: "ON", 6: "ON", 7: "ON"}

    result = controller.set_mode("auto", now)

    assert result["stage"] == "TWO_THREE"
    assert result["wanted"] == desired_lab_relays_for_stage("TWO_THREE")
    assert {command["relay"] for command in result["commands"]} == {2, 3, 6, 7}


def test_priority_controller_entering_manual_preserves_state_and_sends_no_commands():
    controller = PrioritySafetyController(mode="auto")
    controller.confirmed = {2: "ON", 3: "OFF", 7: "ON"}
    result = controller.set_mode("manual", datetime(2026, 6, 18, 10, 0, 0))
    assert result is None
    assert controller.confirmed == {2: "ON", 3: "OFF", 7: "ON"}


def test_priority_controller_monitor_processes_count_with_zero_commands():
    controller = PrioritySafetyController(mode="monitor")
    controller.stable_reads_required = 1
    controller.min_change_ms = 0
    now = datetime(2026, 6, 18, 10, 0, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    payload = {"timestamp": now_ms, "stable_count": 4, "source_healthy": True, "status": "online"}
    result = controller.process_people_count(payload, now)
    assert result["stage"] == "FOUR_PLUS"
    assert result["wanted"] == desired_lab_relays_for_stage("FOUR_PLUS")
    assert result["commands"] == []


def test_priority_controller_zero_count_requires_empty_delay_before_off():
    controller = PrioritySafetyController(mode="auto")
    controller.stable_reads_required = 1
    controller.min_change_ms = 0
    now = datetime(2026, 6, 18, 10, 0, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.latest_count = 0
    controller.last_count_ms = now_ms
    controller.active_stage = "FOUR_PLUS"
    controller.last_known_automation = desired_lab_relays_for_stage("FOUR_PLUS")
    controller.confirmed = desired_lab_relays_for_stage("FOUR_PLUS")

    first = controller.set_mode("auto", now)
    assert first["stage"] == "ZERO_HOLD"
    assert first["commands"] == []

    later = now.replace(minute=6)
    controller.mark_heartbeat(int(later.timestamp() * 1000))
    controller.last_count_ms = int(later.timestamp() * 1000)
    controller.latest_count = 0
    second = controller.reconcile_feedback(later)
    assert second["stage"] == "EMPTY"
    assert second["wanted"] == desired_lab_relays_for_stage("EMPTY")
    assert {command["relay"] for command in second["commands"]} == {2, 3, 4, 6, 7, 8}


def test_priority_controller_positive_count_resets_empty_timer():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 18, 10, 0, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.zero_since_ms = now_ms
    payload = {"timestamp": now_ms, "stable_count": 1, "source_healthy": True, "status": "online"}
    controller.stable_reads_required = 1
    controller.min_change_ms = 0
    controller.process_people_count(payload, now)
    assert controller.zero_since_ms == 0


def test_priority_controller_unknown_feedback_commands_once_until_feedback_changes():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 18, 10, 0, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.latest_count = 1
    controller.last_count_ms = now_ms

    first = controller.reconcile_feedback(now)
    second = controller.reconcile_feedback(now)
    assert {command["relay"] for command in first["commands"]} == {2, 3, 4, 6, 7, 8}
    assert second["commands"] == []


def test_priority_controller_retained_old_feedback_mismatch_corrected_once_in_auto():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 18, 10, 0, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.latest_count = 4
    controller.last_count_ms = now_ms
    controller.confirmed = {2: "OFF", 3: "ON", 4: "ON", 6: "ON", 7: "ON", 8: "ON"}
    controller.last_commanded = {2: "ON"}

    result = controller.set_mode("auto", now)
    assert result["commands"] == [{"relay": 2, "state": "ON"}]
    assert controller.reconcile_feedback(now)["commands"] == []


def test_priority_controller_relay_reconnect_does_not_resync_manual_or_monitor():
    now = datetime(2026, 6, 16, 9, 5, 0)
    now_ms = int(now.timestamp() * 1000)
    for mode in ("manual", "monitor"):
        controller = PrioritySafetyController(mode=mode)
        controller.mark_service_status("online")
        controller.mark_source_status("healthy")
        controller.mark_heartbeat(now_ms)
        controller.latest_count = 7
        controller.last_count_ms = now_ms
        controller.last_commanded = {2: "ON", 7: "ON"}
        controller.confirmed = {2: "ON", 7: "ON"}
        controller.mark_relay_status("offline")
        result = controller.mark_relay_status("online", now)
        assert result["commands"] == []


def test_priority_controller_auto_feedback_mismatch_is_not_manual_override():
    controller = PrioritySafetyController(mode="auto")
    controller.update_confirmed(2, "OFF", infer_manual=False)
    assert controller.manual_overrides == {}
    controller.update_confirmed(2, "OFF", infer_manual=True)
    assert controller.manual_overrides == {2: "OFF"}


def test_priority_controller_periodic_reconcile_corrects_on_mismatch():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 18, 10, 30, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.latest_count = 5
    controller.last_count_ms = now_ms
    controller.confirmed = {2: "OFF", 3: "ON", 4: "OFF", 6: "ON", 7: "ON", 8: "ON"}
    result = controller.reconcile_feedback(now)
    assert result["stage"] == "FOUR_PLUS"
    assert {command["relay"] for command in result["commands"]} == {2, 4}
    assert all(command["state"] == "ON" for command in result["commands"])


def test_priority_controller_periodic_reconcile_corrects_off_mismatch():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 18, 10, 30, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.latest_count = 0
    controller.last_count_ms = now_ms
    controller.active_stage = "EMPTY"
    controller.zero_since_ms = now_ms - controller.zero_off_ms - 1
    controller.last_known_automation = desired_lab_relays_for_stage("EMPTY")
    controller.confirmed = {2: "ON", 3: "OFF", 4: "OFF", 6: "OFF", 7: "ON", 8: "OFF"}
    result = controller.reconcile_feedback(now)
    assert result["stage"] == "EMPTY"
    assert result["commands"] == [{"relay": 2, "state": "OFF"}, {"relay": 7, "state": "OFF"}]


def test_priority_controller_periodic_reconcile_suppressed_outside_auto():
    now = datetime(2026, 6, 18, 10, 30, 0)
    now_ms = int(now.timestamp() * 1000)
    for mode in ("manual", "monitor"):
        controller = PrioritySafetyController(mode=mode)
        controller.mark_service_status("online")
        controller.mark_source_status("healthy")
        controller.mark_heartbeat(now_ms)
        controller.latest_count = 5
        controller.last_count_ms = now_ms
        controller.confirmed = {2: "OFF"}
        assert controller.reconcile_feedback(now)["commands"] == []


def test_priority_controller_periodic_reconcile_no_spam_when_feedback_correct():
    controller = PrioritySafetyController(mode="auto")
    now = datetime(2026, 6, 18, 10, 30, 0)
    now_ms = int(now.timestamp() * 1000)
    controller.mark_service_status("online")
    controller.mark_source_status("healthy")
    controller.mark_heartbeat(now_ms)
    controller.latest_count = 5
    controller.last_count_ms = now_ms
    controller.confirmed = desired_lab_relays_for_stage("FOUR_PLUS")
    first = controller.reconcile_feedback(now)
    second = controller.reconcile_feedback(now)
    assert first["commands"] == []
    assert second["commands"] == []


def test_fallback_window_helper():
    assert is_within_fallback_window(datetime(2026, 6, 16, 8, 30))
    assert is_within_fallback_window(datetime(2026, 6, 16, 13, 15))
    assert not is_within_fallback_window(datetime(2026, 6, 16, 12, 45))


def test_bottom_center_point_and_zone_assignment_pipeline():
    zones = load_zones(str(ROOT / "config" / "zones.json"))
    assert bottom_center_point([100, 200, 140, 360]) == (120, 360)

    class Boxes:
        def __init__(self):
            self.xyxy = FakeTensor([[230, 520, 290, 650], [850, 430, 950, 560], [190, 300, 250, 420], [460, 180, 500, 240]])
            self.id = FakeTensor([11, 22, 33, 44])
            self.conf = FakeTensor([0.8, 0.9, 0.85, 0.2])
            self.cls = FakeTensor([0, 0, 0, 0])

    class Result:
        def __init__(self):
            self.boxes = Boxes()

    counts, assignments = frame_assignments(Result(), zones)
    assert counts[:3] == [1, 1, 1]
    assert assignments[0]["zone"] == 1
    assert assignments[1]["zone"] == 2
    assert assignments[2]["zone"] == 3
    assert assignments[3]["zone"] is None


def test_total_people_assignments_counts_people_without_zones():
    class Boxes:
        def __init__(self):
            self.xyxy = FakeTensor([[10, 20, 50, 100], [60, 30, 100, 120], [0, 0, 10, 10]])
            self.id = FakeTensor([1, 2, 3])
            self.conf = FakeTensor([0.9, 0.8, 0.7])
            self.cls = FakeTensor([0, 0, 2])

    class Result:
        def __init__(self):
            self.boxes = Boxes()

    count, assignments = total_people_assignments(Result())
    assert count == 2
    assert [assignment["zone"] for assignment in assignments] == [None, None]
    assert assignments[0]["bottom_center"] == (30, 100)


def test_display_modes_choose_clean_or_debug_overlay(monkeypatch):
    import numpy as np
    import src.main as main_module

    calls = []

    def fake_total(frame, stable_count, frame_fps, source_status, counting_mode="total-count"):
        calls.append(("total", stable_count, counting_mode))

    def fake_debug(*args, **kwargs):
        calls.append(("debug",))

    monkeypatch.setattr(main_module, "draw_total_count_overlay", fake_total)
    monkeypatch.setattr(main_module, "draw_detection_overlay", fake_debug)
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    common = dict(
        frame=frame,
        assignments=[{"box": [1, 2, 3, 4], "zone": 1}],
        zones=[[(0, 0), (10, 0), (10, 10)]],
        current_zone_counts=[1, 0, 0, 0, 0, 0],
        stable_zone_counts=[1, 0, 0, 0, 0, 0],
        stable_count=1,
        frame_fps=25,
        latency_ms=10,
        source_status="healthy",
        window_samples=3,
        seconds_until_report=57,
        debounced_zone_counts=[1, 0, 0, 0, 0, 0],
    )
    render_display_frame(counting_mode="total-count", **common)
    render_display_frame(counting_mode="zone-count", **common)
    assert calls == [("total", 1, "total-count"), ("debug",)]


def test_each_zone_has_representative_point_and_out_of_zone_returns_none():
    zones = load_zones(str(ROOT / "config" / "zones.json"))
    points = {
        1: (260, 650),
        2: (900, 560),
        3: (220, 420),
        4: (1050, 160),
        5: (620, 160),
        6: (160, 150),
    }
    for expected_zone, point in points.items():
        assert assign_zone(point, zones) == expected_zone
    assert assign_zone((480, 240), zones) is None


def test_count_window_is_time_bounded_and_current_counts_are_separate():
    window = CountWindow(window_seconds=60)
    window.add([1, 0, 0, 0, 0, 0], sample_time=0)
    window.add([2, 0, 0, 0, 0, 0], sample_time=10)
    window.add([3, 0, 0, 0, 0, 0], sample_time=20)
    assert window.current_counts() == [3, 0, 0, 0, 0, 0]
    assert window.medians(now=20) == [2, 0, 0, 0, 0, 0]
    window.add([4, 0, 0, 0, 0, 0], sample_time=85)
    assert window.samples == [[4, 0, 0, 0, 0, 0]]
    assert window.current_counts() == [4, 0, 0, 0, 0, 0]
    assert window.medians(now=85) == [4, 0, 0, 0, 0, 0]


def test_load_zones_returns_live_frame_coordinate_space():
    zones = load_zones(str(ROOT / "config" / "zones.json"))
    assert len(zones) == 6
    for polygon in zones:
        for x, y in polygon:
            assert 0 <= x <= 1280
            assert 0 <= y <= 720


def test_windows_startup_scripts_reference_safe_ai_publisher_contract():
    start_script = (ROOT / "start_lab_automation.ps1").read_text()
    stop_script = (ROOT / "stop_lab_automation.ps1").read_text()
    status_script = (ROOT / "status_lab_automation.ps1").read_text()
    startup_doc = (ROOT / "docs/startup-and-shutdown.md").read_text()
    main_py = (ROOT / "ai-pc/src/main.py").read_text()
    config_yaml = (ROOT / "config/config.yaml").read_text()

    assert ".venv\\Scripts\\python.exe" in start_script
    assert "config\\config.yaml" in start_script
    assert "config\\zones.json" in start_script
    assert "models\\backcam_yolov8s_improved_v3_hardfp.pt" in start_script
    assert "lab/automation/mode_state" in start_script
    assert "lab/vision/heartbeat" in start_script
    assert "labos:1883" not in start_script  # config-driven, not hard-coded
    assert "rtsp://hari:8554/labcam" not in start_script  # config-driven, not hard-coded
    assert "src.main" in start_script
    assert "--display" in start_script
    assert "CountingMode" in start_script
    assert "--counting-mode" in start_script
    assert "logs\\ai-publisher" in start_script
    assert "did not change automation mode" in start_script
    assert "lab/control" not in start_script

    assert "src.main" in stop_script
    assert "Display mode was" in stop_script
    assert "ai-publisher.pid.json" in stop_script

    assert "latest_mode_state" in status_script
    assert "latest_vision_heartbeat_age_seconds" in status_script
    assert "ai_publisher_display" in status_script

    assert 'parser.add_argument("--display"' in main_py
    assert 'parser.add_argument("--counting-mode"' in main_py
    assert "cv2.imshow" in main_py
    assert "Stable Count:" in main_py
    assert "Current Zone Counts:" in main_py
    assert "Stable Zone Counts:" in main_py
    assert "Published Count:" in main_py
    assert "Source:" in main_py
    assert "Mode: {counting_mode}" in main_py
    assert "draw_total_count_overlay" in main_py
    assert "draw_detection_overlay" in main_py
    assert "counting_mode: total-count" in config_yaml

    assert ".\\start_lab_automation.ps1 -DryRun" in startup_doc
    assert ".\\start_lab_automation.ps1 -Display" in startup_doc
    assert ".\\stop_lab_automation.ps1" in startup_doc


def test_node_red_auto_uses_stable_people_count_not_zone_counts():
    flow = json.loads((ROOT / "node-red/flows.json").read_text())
    fn_node = next(node for node in flow if node.get("type") == "function" and node.get("name") == "Priority Safety Controller")
    func = fn_node["func"]
    assert "const count=Number(payload&&payload.stable_count)" in func
    assert "AUTOMATION_COUNT_SOURCE = 'total-count'" in func
    assert "lab/automation/status','online',true" in func
    assert "lab/automation/count_source" in func
    assert "lab/automation/warning',isHealthy?'none':'vision unhealthy -> preserving relay state',true" in func
    assert "lab/automation/warning','none',true" in func
    assert "forceCommandsForUnknownOrMismatch" in func
    assert "correctionFeedback" in func
    assert "stalePreserveTarget" in func
    assert "immediateAutomationTarget" in func
    assert "relay controller offline -> cleared known relay feedback" in func
    assert "relay controller reconnected -> resync desired Auto state" in func
    assert "periodicReconcileTarget" in func
    assert "periodic relay feedback reconciliation" in func
    assert "context.set('actual',{})" in func
    assert "context.set('lastCommand',{})" in func
    assert "if((context.get('mode')||'manual')==='manual'){" in func
    assert "last[relay] && last[relay]!==state" not in func
    assert "stageFor(count)" in func
    assert "payload.zone_counts" not in func
    assert "payload&&payload.zone_counts" not in func
