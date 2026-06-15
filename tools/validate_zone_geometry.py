"""Validate zone geometry and deterministic assignment without changing zone files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def classify(point, zones):
    matches = [index + 1 for index, polygon in enumerate(zones)
               if cv2.pointPolygonTest(np.array(polygon), point, False) >= 0]
    return matches


def validate(zones):
    results = {"centres": [], "vertices": [], "overlap_points": 0}
    for index, polygon in enumerate(zones):
        moments = cv2.moments(np.array(polygon))
        centre = (round(moments["m10"] / moments["m00"]), round(moments["m01"] / moments["m00"]))
        matches = classify(centre, zones)
        results["centres"].append({"zone": index + 1, "point": centre, "matches": matches})
        for vertex in polygon:
            vertex_matches = classify(tuple(vertex), zones)
            results["vertices"].append({"zone": index + 1, "point": vertex, "matches": vertex_matches})
            results["overlap_points"] += int(len(vertex_matches) > 1)
    results["all_centres_unique"] = all(item["matches"] == [item["zone"]] for item in results["centres"])
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zones", default="config/zones.json")
    args = parser.parse_args()
    zones = json.loads(Path(args.zones).read_text())["zones"]
    print(json.dumps(validate(zones), indent=2))


if __name__ == "__main__":
    main()
