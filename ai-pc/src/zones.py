from __future__ import annotations

from dataclasses import dataclass
from statistics import median


Point = tuple[float, float]


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    x, y = point
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        intersects = (yi > y) != (yj > y)
        if intersects and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def assign_zone(point: Point, polygons: list[list[Point]]) -> int | None:
    matches = [index + 1 for index, polygon in enumerate(polygons) if point_in_polygon(point, polygon)]
    return matches[0] if len(matches) == 1 else None


@dataclass
class CountWindow:
    samples: list[list[int]]

    def __init__(self) -> None:
        self.samples = []

    def add(self, counts: list[int]) -> None:
        if len(counts) != 6 or any(not isinstance(value, int) or value < 0 for value in counts):
            raise ValueError("zone counts must be six non-negative integers")
        self.samples.append(counts)

    def clear(self) -> None:
        self.samples.clear()

    def medians(self) -> list[int]:
        if not self.samples:
            raise ValueError("cannot report an empty count window")
        return [int(median(row[index] for row in self.samples)) for index in range(6)]

