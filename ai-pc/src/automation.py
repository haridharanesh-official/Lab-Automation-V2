from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field

from .reporting import validate_report


def desired_relays(zones: list[int]) -> list[bool]:
    occupied = [count > 0 for count in zones]
    return occupied + [
        occupied[0] or occupied[1],
        occupied[1] or occupied[2],
        occupied[3] or occupied[4],
        occupied[4] or occupied[5],
    ]


def stage_for_people_count(count: int) -> str:
    if count <= 0:
        return "EMPTY_STAGE"
    if count < 4:
        return "LOW_STAGE"
    return "HIGH_STAGE"


def desired_lab_relays_for_stage(stage: str) -> dict[int, str]:
    states = {2: "OFF", 3: "OFF", 4: "OFF", 6: "OFF", 7: "OFF", 8: "OFF"}
    if stage == "LOW_STAGE":
        states[2] = "ON"
        states[3] = "ON"
        states[6] = "ON"
        states[7] = "ON"
    elif stage == "HIGH_STAGE":
        for relay in states:
            states[relay] = "ON"
    return states


def is_within_fallback_window(now: datetime) -> bool:
    minutes = now.hour * 60 + now.minute
    morning = 8 * 60 + 30 <= minutes < 12 * 60 + 30
    afternoon = 13 * 60 <= minutes < 16 * 60 + 30
    return morning or afternoon


@dataclass
class AutomationController:
    mode: str = "manual"
    confirmed: list[bool] = field(default_factory=lambda: [False] * 10)
    intended: list[bool] = field(default_factory=lambda: [False] * 10)
    empty_streaks: list[int] = field(default_factory=lambda: [0] * 6)
    last_sequence: int = -1

    def set_mode(self, mode: str) -> None:
        if mode not in {"manual", "monitor", "auto"}:
            raise ValueError("invalid mode")
        self.mode = mode

    def update_confirmed(self, relay: int, state: bool) -> None:
        self.confirmed[relay - 1] = state

    def process(self, report: dict) -> dict:
        valid, reason = validate_report(report)
        if not valid:
            return {"accepted": False, "reason": reason, "commands": []}
        if report["sequence"] <= self.last_sequence:
            return {"accepted": False, "reason": "duplicate or out-of-order sequence", "commands": []}
        self.last_sequence = report["sequence"]
        stable_zones = []
        for index, count in enumerate(report["zones"]):
            if count > 0:
                self.empty_streaks[index] = 0
                stable_zones.append(1)
            else:
                self.empty_streaks[index] += 1
                stable_zones.append(0 if self.empty_streaks[index] >= 2 else int(self.intended[index]))
        self.intended = desired_relays(stable_zones)
        commands = []
        if self.mode == "auto":
            commands = [
                {"relay": index + 1, "state": "ON" if wanted else "OFF"}
                for index, wanted in enumerate(self.intended)
                if wanted != self.confirmed[index]
            ]
        return {"accepted": True, "reason": "ok", "intended": self.intended.copy(), "commands": commands}

    def vision_unavailable(self) -> dict:
        return {"accepted": False, "reason": "vision unavailable; states preserved", "commands": []}


@dataclass
class PrioritySafetyController:
    mode: str = "manual"
    confirmed: dict[int, str] = field(default_factory=dict)
    manual_overrides: dict[int, str] = field(default_factory=dict)
    last_commanded: dict[int, str] = field(default_factory=dict)
    last_correction_feedback: dict[int, str] = field(default_factory=dict)
    last_known_automation: dict[int, str] | None = None
    service_online: bool = False
    source_healthy: bool = False
    last_heartbeat_ms: int = 0
    last_count_ms: int = 0
    latest_count: int | None = None
    latest_count_healthy: bool = False
    active_stage: str = "EMPTY_STAGE"
    high_load_latch: bool = False
    zero_since_ms: int = 0
    last_apply_ms: int = 0
    fresh_ms: int = 15_000
    zero_off_ms: int = 60_000
    relay_online: bool = False
    relay_resync_needed: bool = False

    def set_mode(self, mode: str, now: datetime | None = None) -> dict | None:
        if mode not in {"manual", "monitor", "auto"}:
            raise ValueError("invalid mode")
        was_mode = self.mode
        self.mode = mode
        if mode != "auto":
            self.zero_since_ms = 0
            return None
        if was_mode != "auto":
            self.last_commanded.clear()
            self.last_correction_feedback.clear()
        if now is not None:
            return self.recompute_on_auto_entry(now)
        return None

    def update_confirmed(self, relay: int, state: str, infer_manual: bool = False) -> None:
        value = state.upper()
        self.confirmed[relay] = value
        if infer_manual:
            self.manual_overrides[relay] = value

    def mark_relay_status(self, status: str, now: datetime | None = None) -> dict:
        online = status.lower() == "online"
        was_online = self.relay_online
        self.relay_online = online
        if not online:
            self.confirmed.clear()
            self.last_commanded.clear()
            self.last_correction_feedback.clear()
            self.relay_resync_needed = True
            return {"status": "offline", "commands": []}
        if not was_online and self.relay_resync_needed:
            if now is not None:
                return self.resync_after_relay_online(now)
        return {"status": "online", "commands": []}

    def clear_manual_override(self, relay: int | None = None) -> None:
        if relay is None:
            self.manual_overrides.clear()
        else:
            self.manual_overrides.pop(relay, None)

    def mark_service_status(self, status: str) -> None:
        self.service_online = status.lower() in {"online", "healthy"}
        if not self.service_online:
            self.zero_since_ms = 0

    def mark_source_status(self, status: str) -> None:
        self.source_healthy = status.lower() == "healthy"
        if not self.source_healthy:
            self.zero_since_ms = 0

    def mark_heartbeat(self, now_ms: int) -> None:
        self.last_heartbeat_ms = now_ms

    def vision_is_healthy(self, now_ms: int) -> bool:
        return (
            self.service_online
            and self.source_healthy
            and self.last_heartbeat_ms > 0
            and self.last_count_ms > 0
            and self.latest_count_healthy
            and now_ms - self.last_heartbeat_ms <= self.fresh_ms
        )

    def _apply_manual_overrides(self, states: dict[int, str]) -> dict[int, str]:
        if self.mode != "manual":
            return dict(states)
        applied = dict(states)
        for relay, state in self.manual_overrides.items():
            applied[relay] = state
        return applied

    def _build_commands(self, wanted: dict[int, str]) -> list[dict]:
        commands = []
        for relay, state in wanted.items():
            confirmed = self.confirmed.get(relay)
            feedback_key = confirmed if confirmed is not None else "UNKNOWN"
            if confirmed != state and self.last_correction_feedback.get(relay) != feedback_key:
                commands.append({"relay": relay, "state": state})
                self.last_commanded[relay] = state
                self.last_correction_feedback[relay] = feedback_key
        return commands

    def _force_commands_for_unknown_or_mismatch(self, wanted: dict[int, str]) -> list[dict]:
        return self._build_commands(wanted)

    def _preserve_target(self, reason: str) -> tuple[str, dict[int, str], str]:
        base = dict(self.last_known_automation or self.confirmed)
        return "VISION_STALE", self._apply_manual_overrides(base), reason

    def _stage_for_latch(self, count: int) -> str:
        if count <= 0:
            return "EMPTY_STAGE"
        if count >= 4:
            return "HIGH_STAGE"
        return "HIGH_STAGE" if self.high_load_latch else "LOW_STAGE"

    def resync_after_relay_online(self, now: datetime) -> dict:
        now_ms = int(now.timestamp() * 1000)
        count = self.latest_count
        if self.mode != "auto" or not self.vision_is_healthy(now_ms) or count is None:
            return {"stage": "RELAY_ONLINE_NO_RESYNC", "wanted": {}, "commands": []}
        result = self.recompute_on_auto_entry(now)
        result["reason"] = "relay controller reconnected -> resync desired Auto state"
        self.relay_resync_needed = False
        return result

    def recompute_on_auto_entry(self, now: datetime) -> dict:
        now_ms = int(now.timestamp() * 1000)
        count = self.latest_count
        if self.mode != "auto" or not self.vision_is_healthy(now_ms) or count is None:
            stage, wanted, reason = self._preserve_target("vision unhealthy -> preserving relay state")
            return {"stage": stage, "wanted": wanted, "commands": [], "reason": reason}
        target_stage, wanted, reason = self._immediate_automation_target(count, now_ms)
        commands = [] if target_stage == "ZERO_HOLD" else self._force_commands_for_unknown_or_mismatch(wanted)
        return {"stage": target_stage, "wanted": wanted, "commands": commands, "reason": reason}

    def reconcile_feedback(self, now: datetime) -> dict:
        now_ms = int(now.timestamp() * 1000)
        count = self.latest_count
        if self.mode != "auto" or not self.vision_is_healthy(now_ms) or count is None:
            return {"stage": "RECONCILE_SKIPPED", "wanted": {}, "commands": []}
        stage, wanted, reason = self._immediate_automation_target(count, now_ms)
        commands = [] if stage == "ZERO_HOLD" else self._force_commands_for_unknown_or_mismatch(wanted)
        return {
            "stage": stage,
            "wanted": wanted,
            "commands": commands,
            "reason": f"periodic relay feedback reconciliation: {reason}",
        }

    def _immediate_automation_target(self, count: int, now_ms: int) -> tuple[str, dict[int, str], str]:
        if count == 0:
            if self.zero_since_ms == 0:
                self.zero_since_ms = now_ms
            if now_ms - self.zero_since_ms < self.zero_off_ms:
                base = dict(self.last_known_automation or self.confirmed or desired_lab_relays_for_stage(self.active_stage))
                return "ZERO_HOLD", self._apply_manual_overrides(base), "healthy zero hold"
            self.high_load_latch = False
            stage = "EMPTY_STAGE"
        else:
            self.zero_since_ms = 0
            if count >= 4:
                self.high_load_latch = True
            stage = self._stage_for_latch(count)

        base = desired_lab_relays_for_stage(stage)
        self.active_stage = stage
        self.last_known_automation = dict(base)
        self.last_apply_ms = now_ms
        return stage, self._apply_manual_overrides(base), f"applied {stage}"

    def process_people_count(self, payload: dict, now: datetime) -> dict:
        now_ms = int(now.timestamp() * 1000)
        if not isinstance(payload, dict):
            return {"accepted": False, "reason": "invalid payload", "commands": []}
        count = payload.get("stable_count")
        ts = int(payload.get("timestamp", 0))
        if ts < 100_000_000_000:
            ts *= 1000
        valid = (
            payload.get("source_healthy") is True
            and payload.get("status") == "online"
            and isinstance(count, int)
            and count >= 0
            and abs(now_ms - ts) <= self.fresh_ms
        )
        if not valid:
            self.latest_count_healthy = False
            self.zero_since_ms = 0
            target_stage, wanted, reason = self._preserve_target("vision unhealthy -> preserving relay state")
            commands = []
            return {"accepted": False, "reason": reason, "stage": target_stage, "wanted": wanted, "commands": commands}

        self.latest_count = count
        self.last_count_ms = now_ms
        self.latest_count_healthy = True
        if self.mode == "manual":
            stage, wanted, reason = self._preserve_target("manual mode -> preserving relay state")
            return {
                "accepted": True,
                "reason": reason,
                "stage": stage,
                "wanted": wanted,
                "commands": [],
                "manual_overrides": dict(self.manual_overrides),
            }
        target_stage, wanted, reason = (
            self._immediate_automation_target(count, now_ms)
            if self.vision_is_healthy(now_ms)
            else self._preserve_target("vision unhealthy -> preserving relay state")
        )
        commands = self._build_commands(wanted) if self.mode == "auto" and target_stage not in {"ZERO_HOLD"} else []
        return {
            "accepted": True,
            "reason": reason,
            "stage": target_stage,
            "wanted": wanted,
            "commands": commands,
            "manual_overrides": dict(self.manual_overrides),
        }
