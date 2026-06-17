from __future__ import annotations

from dataclasses import dataclass
from statistics import median
import time

import cv2
import numpy as np


Point = tuple[float, float]


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    if len(polygon) < 3:
        return False
    return cv2.pointPolygonTest(np.array(polygon, dtype=np.int32), point, False) >= 0


def assign_zone(point: Point, polygons: list[list[Point]]) -> int | None:
    matches = [index + 1 for index, polygon in enumerate(polygons) if point_in_polygon(point, polygon)]
    return matches[0] if len(matches) == 1 else None


@dataclass
class CountWindow:
    samples: list[list[int]]
    sample_times: list[float]
    window_seconds: float

    def __init__(self, window_seconds: float = 60) -> None:
        self.samples = []
        self.sample_times = []
        self.window_seconds = float(window_seconds)

    def _trim(self, now: float | None = None) -> None:
        if now is None:
            now = time.monotonic()
        cutoff = now - self.window_seconds
        while self.sample_times and self.sample_times[0] < cutoff:
            self.sample_times.pop(0)
            self.samples.pop(0)

    def add(self, counts: list[int], sample_time: float | None = None) -> None:
        if len(counts) != 6 or any(not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("zone counts must be six non-negative integers")
        if sample_time is None:
            sample_time = time.monotonic()
        self.samples.append(counts)
        self.sample_times.append(float(sample_time))
        self._trim(sample_time)

    def clear(self) -> None:
        self.samples.clear()
        self.sample_times.clear()

    def current_counts(self) -> list[int]:
        return list(self.samples[-1]) if self.samples else [0] * 6

    def sample_count(self) -> int:
        return len(self.samples)

    def seconds_until_report(self, now: float | None = None) -> float:
        if not self.sample_times:
            return self.window_seconds
        if now is None:
            now = time.monotonic()
        elapsed = now - self.sample_times[0]
        return max(0.0, self.window_seconds - elapsed)

    def medians(self, now: float | None = None) -> list[int]:
        self._trim(now)
        if not self.samples:
            raise ValueError("cannot report an empty count window")
        return [int(median(row[index] for row in self.samples)) for index in range(6)]
