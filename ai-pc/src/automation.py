from __future__ import annotations

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

