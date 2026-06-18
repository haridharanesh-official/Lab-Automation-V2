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
        return "EMPTY"
    if count == 1:
        return "ONE"
    if count < 4:
        return "TWO_THREE"
    return "FOUR_PLUS"


def desired_lab_relays_for_stage(stage: str) -> dict[int, str]:
    states = {2: "OFF", 3: "OFF", 4: "OFF", 6: "OFF", 7: "OFF", 8: "OFF"}
    if stage == "ONE":
        states[2] = "ON"
        states[7] = "ON"
    elif stage == "TWO_THREE":
        states[2] = "ON"
        states[3] = "ON"
        states[6] = "ON"
        states[7] = "ON"
    elif stage == "FOUR_PLUS":
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
    last_known_automation: dict[int, str] | None = None
    service_online: bool = False
    source_healthy: bool = False
    last_heartbeat_ms: int = 0
    last_count_ms: int = 0
    latest_count: int | None = None
    active_stage: str = "EMPTY"
    pending_stage: str = ""
    pending_reads: int = 0
    zero_since_ms: int = 0
    fallback_off_since_ms: int = 0
    last_apply_ms: int = 0
    stable_reads_required: int = 3
    fresh_ms: int = 15_000
    zero_off_ms: int = 300_000
    min_change_ms: int = 8_000
    outside_window_off_delay_ms: int = 300_000
    relay_online: bool = False
    relay_resync_needed: bool = False

    def set_mode(self, mode: str) -> None:
        if mode not in {"manual", "monitor", "auto"}:
            raise ValueError("invalid mode")
        self.mode = mode
        if mode != "auto":
            self.zero_since_ms = 0
            self.fallback_off_since_ms = 0

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

    def mark_source_status(self, status: str) -> None:
        self.source_healthy = status.lower() == "healthy"

    def mark_heartbeat(self, now_ms: int) -> None:
        self.last_heartbeat_ms = now_ms

    def vision_is_healthy(self, now_ms: int) -> bool:
        return (
            self.service_online
            and self.source_healthy
            and self.last_heartbeat_ms > 0
            and self.last_count_ms > 0
            and now_ms - self.last_heartbeat_ms <= self.fresh_ms
            and now_ms - self.last_count_ms <= self.fresh_ms
        )

    def _apply_manual_overrides(self, states: dict[int, str]) -> dict[int, str]:
        applied = dict(states)
        for relay, state in self.manual_overrides.items():
            applied[relay] = state
        return applied

    def _build_commands(self, wanted: dict[int, str]) -> list[dict]:
        commands = []
        for relay, state in wanted.items():
            confirmed = self.confirmed.get(relay)
            last = self.last_commanded.get(relay)
            if confirmed != state and last != state:
                commands.append({"relay": relay, "state": state})
                self.last_commanded[relay] = state
        return commands

    def _force_commands_for_unknown_or_mismatch(self, wanted: dict[int, str]) -> list[dict]:
        commands = []
        for relay, state in wanted.items():
            if self.confirmed.get(relay) != state:
                commands.append({"relay": relay, "state": state})
                self.last_commanded[relay] = state
        return commands

    def resync_after_relay_online(self, now: datetime) -> dict:
        now_ms = int(now.timestamp() * 1000)
        count = self.latest_count
        if self.mode != "auto" or not self.vision_is_healthy(now_ms) or count is None or count <= 0:
            return {"stage": "RELAY_ONLINE_NO_RESYNC", "wanted": {}, "commands": []}
        stage = stage_for_people_count(count)
        base = desired_lab_relays_for_stage(stage)
        self.active_stage = stage
        self.last_known_automation = dict(base)
        wanted = self._apply_manual_overrides(base)
        commands = self._force_commands_for_unknown_or_mismatch(wanted)
        self.relay_resync_needed = False
        return {
            "stage": stage,
            "wanted": wanted,
            "commands": commands,
            "reason": "relay controller reconnected -> resync desired Auto state",
        }

    def reconcile_feedback(self, now: datetime) -> dict:
        now_ms = int(now.timestamp() * 1000)
        count = self.latest_count
        if self.mode != "auto" or not self.vision_is_healthy(now_ms) or count is None:
            return {"stage": "RECONCILE_SKIPPED", "wanted": {}, "commands": []}
        if count > 0:
            stage = stage_for_people_count(count)
            base = desired_lab_relays_for_stage(stage)
        else:
            stage = self.active_stage
            base = dict(self.last_known_automation or desired_lab_relays_for_stage(stage))
        wanted = self._apply_manual_overrides(base)
        commands = self._force_commands_for_unknown_or_mismatch(wanted)
        return {
            "stage": stage,
            "wanted": wanted,
            "commands": commands,
            "reason": "periodic relay feedback reconciliation",
        }

    def _fallback_target(self, now: datetime, now_ms: int) -> tuple[str, dict[int, str], str]:
        within_window = is_within_fallback_window(now)
        if within_window:
            self.fallback_off_since_ms = 0
            base = dict(self.last_known_automation or desired_lab_relays_for_stage("FOUR_PLUS"))
            return "TIMETABLE_FALLBACK", self._apply_manual_overrides(base), "vision unhealthy -> timetable fallback"

        if self.fallback_off_since_ms == 0:
            self.fallback_off_since_ms = now_ms
        if now_ms - self.fallback_off_since_ms < self.outside_window_off_delay_ms:
            base = dict(self.last_known_automation or desired_lab_relays_for_stage("FOUR_PLUS"))
            return "TIMETABLE_HOLD", self._apply_manual_overrides(base), "vision unhealthy -> preserving last known state outside timetable"

        return "TIMETABLE_OFF", self._apply_manual_overrides(desired_lab_relays_for_stage("EMPTY")), "vision unhealthy -> safe delayed off outside timetable"

    def _automation_target(self, count: int, now_ms: int) -> tuple[str, dict[int, str], str]:
        stage = stage_for_people_count(count)
        if count == 0:
            if self.zero_since_ms == 0:
                self.zero_since_ms = now_ms
            if now_ms - self.zero_since_ms < self.zero_off_ms:
                base = dict(self.last_known_automation or desired_lab_relays_for_stage(self.active_stage))
                return "ZERO_HOLD", self._apply_manual_overrides(base), "healthy zero hold"
        else:
            self.zero_since_ms = 0

        if stage == self.active_stage:
            base = dict(self.last_known_automation or desired_lab_relays_for_stage(stage))
            return stage, self._apply_manual_overrides(base), "stage unchanged"

        if stage == self.pending_stage:
            self.pending_reads += 1
        else:
            self.pending_stage = stage
            self.pending_reads = 1

        if self.pending_reads < self.stable_reads_required or now_ms - self.last_apply_ms < self.min_change_ms:
            base = dict(self.last_known_automation or desired_lab_relays_for_stage(self.active_stage))
            return "STABILIZING", self._apply_manual_overrides(base), f"stabilizing {stage}"

        self.pending_stage = ""
        self.pending_reads = 0
        self.active_stage = stage
        self.last_apply_ms = now_ms
        base = desired_lab_relays_for_stage(stage)
        self.last_known_automation = dict(base)
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
            target_stage, wanted, reason = self._fallback_target(now, now_ms)
            commands = self._build_commands(wanted) if self.mode == "auto" else []
            return {"accepted": False, "reason": reason, "stage": target_stage, "wanted": wanted, "commands": commands}

        self.latest_count = count
        self.last_count_ms = now_ms
        target_stage, wanted, reason = (
            self._automation_target(count, now_ms)
            if self.vision_is_healthy(now_ms)
            else self._fallback_target(now, now_ms)
        )
        commands = self._build_commands(wanted) if self.mode == "auto" and target_stage not in {"STABILIZING"} else []
        return {
            "accepted": True,
            "reason": reason,
            "stage": target_stage,
            "wanted": wanted,
            "commands": commands,
            "manual_overrides": dict(self.manual_overrides),
        }
