"""OpenCV six-zone polygon editor for Lab Automation calibration.

Calibration-only: this tool never publishes MQTT, changes automation modes, or
controls relays.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import cv2
import numpy as np


VALIDATOR_PATH = Path(__file__).with_name("validate_zones.py")
spec = importlib.util.spec_from_file_location("validate_zones", VALIDATOR_PATH)
validate_zones = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = validate_zones
spec.loader.exec_module(validate_zones)


COLORS = {
    1: (90, 220, 255),
    2: (70, 255, 120),
    3: (255, 200, 80),
    4: (255, 120, 210),
    5: (170, 150, 255),
    6: (120, 220, 160),
}


class ZoneEditor:
    def __init__(self, image, image_name: str, zones_path: str) -> None:
        self.image = image
        self.image_name = image_name
        self.zones_path = zones_path
        height, width = image.shape[:2]
        self.document, self.load_warnings = validate_zones.load_zone_document(zones_path, width, height)
        self.document["image_width"] = width
        self.document["image_height"] = height
        self.active_zone = 1
        self.test_mode = False
        self.help_visible = True
        self.status = "; ".join(self.load_warnings) if self.load_warnings else "ready"
        self.last_test = ""

    def zones(self) -> list[dict]:
        return self.document["zones"]

    def active_points(self) -> list[list[int]]:
        return self.zones()[self.active_zone - 1]["points"]

    def add_point(self, x: int, y: int) -> None:
        if self.test_mode:
            result = validate_zones.assign_point_to_zone((x, y), self.document)
            zone = result["zone"]
            if zone is None:
                self.last_test = f"Point ({x},{y}) -> UNKNOWN"
            elif result["status"] == "OVERLAP":
                self.last_test = f"Point ({x},{y}) -> Zone {zone}; overlap {result['matches']}"
            else:
                self.last_test = f"Point ({x},{y}) -> Zone {zone}"
            self.status = self.last_test
            return
        self.active_points().append([int(x), int(y)])
        self.status = f"added point to Zone {self.active_zone}: ({x},{y})"

    def undo(self) -> None:
        points = self.active_points()
        if points:
            removed = points.pop()
            self.status = f"removed Zone {self.active_zone} point {removed}"
        else:
            self.status = f"Zone {self.active_zone} has no points"

    def clear_active(self) -> None:
        self.active_points().clear()
        self.status = f"cleared Zone {self.active_zone}"

    def reset_all(self) -> None:
        for zone in self.zones():
            zone["points"] = []
        self.status = "all zones reset"

    def load_existing(self) -> None:
        height, width = self.image.shape[:2]
        self.document, warnings = validate_zones.load_zone_document(self.zones_path, width, height)
        self.document["image_width"] = width
        self.document["image_height"] = height
        self.status = "; ".join(warnings) if warnings else f"loaded {self.zones_path}"

    def backup(self) -> None:
        backup = validate_zones.create_backup(self.zones_path)
        self.status = f"backup created: {backup}" if backup else "no zones.json exists to back up"

    def save(self) -> None:
        validation = validate_zones.validate_zone_document(self.document)
        if not validation.valid:
            self.status = "SAVE BLOCKED: " + "; ".join(validation.errors)
            return
        backup = validate_zones.save_zone_document(self.zones_path, self.document)
        warning_text = (" warnings: " + "; ".join(validation.warnings)) if validation.warnings else ""
        backup_text = f" backup: {backup}" if backup else " no previous file"
        self.status = f"saved {self.zones_path};{backup_text}{warning_text}"

    def draw(self):
        canvas = self.image.copy()
        overlay = canvas.copy()
        for zone in self.zones():
            zone_id = int(zone["id"])
            points = zone.get("points", [])
            color = COLORS.get(zone_id, (220, 220, 220))
            for point in points:
                cv2.circle(canvas, tuple(point), 5, color, -1, cv2.LINE_AA)
            if len(points) >= 2:
                pts = np.array(points, dtype=np.int32)
                cv2.polylines(canvas, [pts], len(points) >= 3, color, 2, cv2.LINE_AA)
            if len(points) >= 3:
                pts = np.array(points, dtype=np.int32)
                cv2.fillPoly(overlay, [pts], color)
                moments = cv2.moments(pts)
                if moments["m00"]:
                    cx = int(moments["m10"] / moments["m00"])
                    cy = int(moments["m01"] / moments["m00"])
                else:
                    cx, cy = points[0]
                label = f"Z{zone_id}"
                cv2.putText(canvas, label, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2, cv2.LINE_AA)
        canvas = cv2.addWeighted(overlay, 0.18, canvas, 0.82, 0)
        self.draw_overlay_text(canvas)
        return canvas

    def draw_overlay_text(self, canvas) -> None:
        lines = [
            f"{self.image_name} | active Zone {self.active_zone} | test mode {'ON' if self.test_mode else 'OFF'}",
            self.status,
        ]
        if self.help_visible:
            lines.extend(
                [
                    "1-6 select | left-click add/test | right-click or U undo",
                    "C clear zone | R reset all | T test point | S save | L load | B backup | H help | Q/Esc quit",
                    "Save is blocked for missing zones, invalid polygons, or out-of-bounds points.",
                ]
            )
        y = 28
        for line in lines:
            cv2.putText(canvas, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (20, 20, 20), 4, cv2.LINE_AA)
            cv2.putText(canvas, line, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (245, 245, 245), 1, cv2.LINE_AA)
            y += 25


def load_image(args):
    if args.image:
        image = cv2.imread(args.image)
        if image is None:
            raise SystemExit(f"could not load image: {args.image}")
        return image, args.image
    if args.rtsp:
        capture = cv2.VideoCapture(args.rtsp)
        try:
            if not capture.isOpened():
                raise SystemExit(f"could not open RTSP stream: {args.rtsp}")
            ok, frame = capture.read()
            if not ok or frame is None:
                raise SystemExit("RTSP stream opened but no frame was returned")
            return frame, args.rtsp
        finally:
            capture.release()
    raise SystemExit("provide --image or --rtsp")


def confirm_reset() -> bool:
    print("Reset all zones? Type RESET and press Enter to confirm:")
    return input("> ").strip() == "RESET"


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenCV six-zone polygon editor.")
    parser.add_argument("--image", help="snapshot/image file to edit")
    parser.add_argument("--rtsp", nargs="?", const="rtsp://hari:8554/labcam", help="capture one frame from RTSP")
    parser.add_argument("--zones", default="config/zones.json")
    args = parser.parse_args()
    image, image_name = load_image(args)
    editor = ZoneEditor(image, image_name, args.zones)

    def mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            editor.add_point(x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            editor.undo()

    cv2.namedWindow("Lab Zone Editor", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("Lab Zone Editor", mouse)
    while True:
        cv2.imshow("Lab Zone Editor", editor.draw())
        key = cv2.waitKey(30) & 0xFF
        if key in (27, ord("q")):
            break
        if ord("1") <= key <= ord("6"):
            editor.active_zone = key - ord("0")
            editor.status = f"selected Zone {editor.active_zone}"
        elif key in (ord("u"), 8):
            editor.undo()
        elif key == ord("c"):
            editor.clear_active()
        elif key == ord("r") and confirm_reset():
            editor.reset_all()
        elif key == ord("t"):
            editor.test_mode = not editor.test_mode
            editor.status = f"point-test mode {'enabled' if editor.test_mode else 'disabled'}"
        elif key == ord("s"):
            editor.save()
        elif key == ord("l"):
            editor.load_existing()
        elif key == ord("b"):
            editor.backup()
        elif key == ord("h"):
            editor.help_visible = not editor.help_visible
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
