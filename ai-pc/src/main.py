"""Production vision entry point. Defaults to monitor mode and publishes telemetry only."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import paho.mqtt.client as mqtt
import yaml
from ultralytics import YOLO

from .mqtt_publisher import VisionPublisher
from .reporting import build_report
from .zones import CountWindow
from .zones import assign_zone


COUNTING_MODES = {"total-count", "zone-count"}


class DebouncedPeopleCount:
    """Keeps HA/automation people count stable through brief missed detections."""

    def __init__(self, stable_seconds: float = 3.0, zero_hold_seconds: float = 10.0) -> None:
        self.stable_seconds = float(stable_seconds)
        self.zero_hold_seconds = float(zero_hold_seconds)
        self.published_zone_counts = [0] * 6
        self.candidate_zone_counts: list[int] | None = None
        self.candidate_since: float | None = None

    def update(self, raw_zone_counts: list[int], now: float, source_healthy: bool) -> list[int]:
        if not source_healthy:
            self.candidate_zone_counts = None
            self.candidate_since = None
            return list(self.published_zone_counts)

        raw_zone_counts = list(raw_zone_counts)
        if raw_zone_counts == self.published_zone_counts:
            self.candidate_zone_counts = None
            self.candidate_since = None
            return list(self.published_zone_counts)

        if raw_zone_counts != self.candidate_zone_counts:
            self.candidate_zone_counts = raw_zone_counts
            self.candidate_since = now
            return list(self.published_zone_counts)

        hold_seconds = self.zero_hold_seconds if sum(raw_zone_counts) == 0 else self.stable_seconds
        if self.candidate_since is not None and now - self.candidate_since >= hold_seconds:
            self.published_zone_counts = raw_zone_counts
            self.candidate_zone_counts = None
            self.candidate_since = None

        return list(self.published_zone_counts)


def camera_interrupted(window: CountWindow) -> None:
    window.clear()


def load_config(path: str) -> dict:
    raw = Path(path).read_text()
    return json.loads(raw) if path.endswith(".json") else yaml.safe_load(raw)


def load_zones(path: str) -> list[list[tuple[int, int]]]:
    zone_path = Path(path)
    if not zone_path.exists():
        return []
    data = json.loads(zone_path.read_text())
    return [[tuple(point) for point in polygon] for polygon in data.get("zones", [])]


def normalize_counting_mode(value: str | None) -> str:
    mode = str(value or "total-count").strip().lower()
    if mode not in COUNTING_MODES:
        raise ValueError("counting_mode must be 'total-count' or 'zone-count'")
    return mode


def bottom_center_point(box: list[int]) -> tuple[int, int]:
    return (int((box[0] + box[2]) // 2), int(box[3]))


def frame_assignments(result, zones: list[list[tuple[int, int]]]) -> tuple[list[int], list[dict]]:
    counts = [0] * 6
    assignments: list[dict] = []
    if result.boxes is None:
        return counts, assignments
    track_ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else []
    confidences = result.boxes.conf.cpu().tolist() if result.boxes.conf is not None else []
    classes = result.boxes.cls.int().cpu().tolist() if result.boxes.cls is not None else []
    for index, raw_box in enumerate(result.boxes.xyxy.cpu().tolist()):
        if classes and classes[index] != 0:
            continue
        box = [int(round(value)) for value in raw_box]
        bottom_center = bottom_center_point(box)
        zone = assign_zone(bottom_center, zones)
        if zone is not None and 1 <= zone <= 6:
            counts[zone - 1] += 1
        assignments.append(
            {
                "box": box,
                "bottom_center": bottom_center,
                "zone": zone,
                "confidence": confidences[index] if index < len(confidences) else 0.0,
                "track_id": track_ids[index] if index < len(track_ids) else None,
            }
        )
    return counts, assignments


def total_people_assignments(result) -> tuple[int, list[dict]]:
    assignments: list[dict] = []
    if result.boxes is None:
        return 0, assignments
    track_ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else []
    confidences = result.boxes.conf.cpu().tolist() if result.boxes.conf is not None else []
    classes = result.boxes.cls.int().cpu().tolist() if result.boxes.cls is not None else []
    for index, raw_box in enumerate(result.boxes.xyxy.cpu().tolist()):
        if classes and classes[index] != 0:
            continue
        box = [int(round(value)) for value in raw_box]
        assignments.append(
            {
                "box": box,
                "bottom_center": bottom_center_point(box),
                "zone": None,
                "confidence": confidences[index] if index < len(confidences) else 0.0,
                "track_id": track_ids[index] if index < len(track_ids) else None,
            }
        )
    return len(assignments), assignments


def publish_status(
    publisher: VisionPublisher,
    source_status: str,
    stable_count: int,
    stable_zone_counts: list[int],
    current_zone_counts: list[int],
    debounced_zone_counts: list[int],
    frame_fps: float,
    latency_ms: float,
    counting_mode: str = "zone-count",
) -> None:
    now_ms = int(time.time() * 1000)
    counting_mode = normalize_counting_mode(counting_mode)
    zone_counts_payload = debounced_zone_counts if counting_mode == "zone-count" else None
    raw_zone_counts_payload = current_zone_counts if counting_mode == "zone-count" else None
    window_zone_counts_payload = stable_zone_counts if counting_mode == "zone-count" else None
    publisher.publish("lab/vision/status", "online", retain=True)
    publisher.publish("lab/vision/source_status", source_status, retain=True)
    raw_payload = {
        "publisher": "labvision-ai-pc",
        "timestamp": now_ms,
        "total_count": sum(current_zone_counts),
        "raw_total_count": sum(current_zone_counts),
        "raw_zone_counts": raw_zone_counts_payload,
        "counting_mode": counting_mode,
        "source_healthy": source_status == "healthy",
        "status": "online",
        "fps": round(frame_fps, 3),
        "inference_ms": round(latency_ms, 3),
    }
    publisher.publish("lab/vision/raw_people_count", raw_payload, retain=False)
    publisher.publish(
        "lab/vision/people_count",
        {
            "publisher": "labvision-ai-pc",
            "timestamp": now_ms,
            "total_count": sum(debounced_zone_counts),
            "stable_count": sum(debounced_zone_counts),
            "zone_counts": zone_counts_payload,
            "window_stable_count": stable_count,
            "window_zone_counts": window_zone_counts_payload,
            "raw_total_count": sum(current_zone_counts),
            "raw_zone_counts": raw_zone_counts_payload,
            "debounced": True,
            "counting_mode": counting_mode,
            "source_healthy": source_status == "healthy",
            "status": "online",
            "fps": round(frame_fps, 3),
            "inference_ms": round(latency_ms, 3),
        },
        retain=False,
    )


def zone_color(index: int) -> tuple[int, int, int]:
    colors = [
        (0, 102, 255),
        (0, 200, 255),
        (0, 200, 0),
        (255, 128, 0),
        (255, 0, 255),
        (255, 0, 0),
    ]
    return colors[index % len(colors)]


def draw_zone_overlay(frame, zones: list[list[tuple[int, int]]], current_zone_counts: list[int],
                      stable_zone_counts: list[int]) -> None:
    for index, polygon in enumerate(zones):
        if not polygon:
            continue
        pts = np.array(polygon, dtype=np.int32)
        color = zone_color(index)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color)
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
        cv2.polylines(frame, [pts], True, color, 2, cv2.LINE_AA)
        moments = cv2.moments(pts)
        if moments["m00"]:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            cx, cy = polygon[0]
        cv2.putText(
            frame,
            f"Z{index + 1} C:{current_zone_counts[index]} S:{stable_zone_counts[index]}",
            (cx - 60, cy),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def draw_detection_overlay(frame, assignments: list[dict], zones: list[list[tuple[int, int]]],
                           current_zone_counts: list[int], stable_zone_counts: list[int], stable_count: int,
                           frame_fps: float, latency_ms: float, source_status: str,
                           window_samples: int, seconds_until_report: float,
                           debounced_zone_counts: list[int] | None = None) -> None:
    draw_zone_overlay(frame, zones, current_zone_counts, stable_zone_counts)
    if assignments:
        for assignment in assignments:
            box = assignment["box"]
            bottom_center = assignment["bottom_center"]
            zone = assignment["zone"]
            color = zone_color(zone - 1) if zone is not None and 1 <= zone <= 6 else (255, 255, 255)
            confidence = assignment["confidence"]
            track_id = assignment["track_id"]
            label = f"person {confidence:.2f}"
            if track_id is not None:
                label = f"ID {track_id} {confidence:.2f}"
            cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
            cv2.circle(frame, bottom_center, 5, color, -1)
            cv2.putText(
                frame,
                label,
                (box[0], max(25, box[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )
            if zone is not None:
                cv2.putText(
                    frame,
                    f"Z{zone}",
                    (bottom_center[0] + 6, bottom_center[1] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                    cv2.LINE_AA,
                )
            else:
                cv2.drawMarker(frame, bottom_center, (0, 0, 255), cv2.MARKER_TILTED_CROSS, 16, 2, cv2.LINE_AA)
                cv2.putText(
                    frame,
                    "OUT",
                    (bottom_center[0] + 6, bottom_center[1] - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )

    lines = [
        f"Current Zone Counts: {current_zone_counts}",
        f"Stable Zone Counts: {stable_zone_counts}",
        f"Stable Count: {stable_count}",
        f"Published Count: {sum(debounced_zone_counts or stable_zone_counts)}",
        f"Window Samples: {window_samples}",
        f"Seconds Until Report: {seconds_until_report:.1f}",
        f"FPS: {frame_fps:.2f}",
        f"Inference: {latency_ms:.1f} ms",
        f"Source: {source_status}",
    ]
    panel_height = 28 + (len(lines) * 24)
    cv2.rectangle(frame, (10, 10), (500, panel_height), (0, 0, 0), -1)
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (20, 35 + (index * 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def draw_total_count_overlay(
    frame,
    stable_count: int,
    frame_fps: float,
    source_status: str,
    counting_mode: str = "total-count",
) -> None:
    lines = [
        f"Mode: {counting_mode}",
        f"Stable Count: {stable_count}",
        f"FPS: {frame_fps:.2f}",
        f"Source: {source_status}",
    ]
    cv2.rectangle(frame, (10, 10), (290, 118), (0, 0, 0), -1)
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (20, 35 + (index * 24)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )


def render_display_frame(
    frame,
    counting_mode: str,
    assignments: list[dict],
    zones: list[list[tuple[int, int]]],
    current_zone_counts: list[int],
    stable_zone_counts: list[int],
    stable_count: int,
    frame_fps: float,
    latency_ms: float,
    source_status: str,
    window_samples: int,
    seconds_until_report: float,
    debounced_zone_counts: list[int],
):
    annotated = frame.copy()
    if normalize_counting_mode(counting_mode) == "total-count":
        draw_total_count_overlay(annotated, sum(debounced_zone_counts), frame_fps, source_status)
    else:
        draw_detection_overlay(
            annotated,
            assignments,
            zones,
            current_zone_counts,
            stable_zone_counts,
            stable_count,
            frame_fps,
            latency_ms,
            source_status,
            window_samples,
            seconds_until_report,
            debounced_zone_counts,
        )
    return annotated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="validate configuration without opening camera or MQTT")
    parser.add_argument("--duration", type=float, default=0, help="optional runtime limit in seconds; 0 means run until stopped")
    parser.add_argument("--display", action="store_true", help="show a live OpenCV overlay window while publishing")
    parser.add_argument("--counting-mode", choices=sorted(COUNTING_MODES), help="override config counting_mode")
    args = parser.parse_args()
    config = load_config(args.config)
    counting_mode = normalize_counting_mode(args.counting_mode or config.get("counting_mode", "total-count"))
    if args.dry_run:
        config["counting_mode"] = counting_mode
        print(json.dumps(config, indent=2))
        return

    if str(config.get("mode", "monitor")).lower() != "monitor":
        raise SystemExit("vision runtime refuses non-monitor mode")

    mqtt_config = config.get("mqtt", {})
    if not mqtt_config.get("enabled", False):
        raise SystemExit("mqtt.enabled must be true for live publisher mode")

    camera = config["camera"]
    model_config = config["model"]
    zones = load_zones(config.get("zones_path", "config/zones.json")) if counting_mode == "zone-count" else []
    if counting_mode == "zone-count" and len(zones) != 6:
        raise SystemExit("zone-count mode requires config/zones.json with six polygons")
    model = YOLO(model_config["path"])

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if mqtt_config.get("username"):
        client.username_pw_set(mqtt_config["username"], mqtt_config.get("password", ""))
    client.connect(mqtt_config["host"], int(mqtt_config.get("port", 1883)), 10)
    client.loop_start()
    publisher = VisionPublisher(client)

    publisher.publish("lab/vision/status", "online", retain=True)
    publisher.publish("lab/vision/source_status", "starting", retain=True)
    publisher.publish("lab/vision/heartbeat", json.dumps({"publisher": "labvision-ai-pc", "timestamp": int(time.time())}))

    cap = None
    window = CountWindow(window_seconds=float(config.get("report_seconds", 60)))
    debouncer = DebouncedPeopleCount(
        stable_seconds=float(config.get("people_count_stable_seconds", 3)),
        zero_hold_seconds=float(config.get("people_count_zero_hold_seconds", 10)),
    )
    last_heartbeat = 0.0
    last_publish = 0.0
    started = time.monotonic()
    last_frame_time = started
    source_status = "starting"

    try:
        while True:
            if args.duration and time.monotonic() - started >= args.duration:
                break
            if cap is None:
                cap = cv2.VideoCapture(camera["url"], cv2.CAP_FFMPEG)
                if not cap.isOpened():
                    source_status = "unhealthy"
                    publisher.publish("lab/vision/source_status", source_status, retain=True)
                    time.sleep(float(camera.get("reconnect_seconds", 5)))
                    continue
                source_status = "healthy"
                publisher.publish("lab/vision/source_status", source_status, retain=True)
            ok, frame = cap.read()
            if not ok:
                source_status = "unhealthy"
                publisher.publish("lab/vision/source_status", source_status, retain=True)
                camera_interrupted(window)
                cap.release()
                cap = None
                time.sleep(float(camera.get("reconnect_seconds", 5)))
                continue

            now = time.monotonic()
            frame_fps = 1 / (now - last_frame_time) if now > last_frame_time else 0.0
            last_frame_time = now
            tick = time.perf_counter()
            result = model.track(
                frame,
                persist=True,
                classes=[0],
                conf=float(model_config["confidence"]),
                imgsz=int(model_config["image_size"]),
                device=model_config["device"],
                tracker=model_config["tracker"],
                verbose=False,
            )[0]
            latency_ms = (time.perf_counter() - tick) * 1000
            if counting_mode == "zone-count":
                current_zone_counts, assignments = frame_assignments(result, zones)
            else:
                total_count, assignments = total_people_assignments(result)
                current_zone_counts = [total_count, 0, 0, 0, 0, 0]
            window.add(current_zone_counts, sample_time=now)
            stable_zone_counts = window.medians(now)
            stable_count = sum(stable_zone_counts)
            debounced_zone_counts = debouncer.update(stable_zone_counts, now, source_status == "healthy")

            if now - last_publish >= 1.0:
                publish_status(
                    publisher,
                    source_status,
                    stable_count,
                    stable_zone_counts,
                    current_zone_counts,
                    debounced_zone_counts,
                    frame_fps,
                    latency_ms,
                    counting_mode,
                )
                last_publish = now
            if now - last_heartbeat >= float(config.get("heartbeat_seconds", 10)):
                publisher.publish(
                    "lab/vision/heartbeat",
                    {"publisher": "labvision-ai-pc", "timestamp": int(time.time()), "status": "online"},
                    retain=False,
                )
                last_heartbeat = now
            if args.display:
                annotated = render_display_frame(
                    frame,
                    counting_mode,
                    assignments,
                    zones,
                    current_zone_counts,
                    stable_zone_counts,
                    stable_count,
                    frame_fps,
                    latency_ms,
                    source_status,
                    window.sample_count(),
                    window.seconds_until_report(now),
                    debounced_zone_counts,
                )
                cv2.imshow("Lab Automation v2.0 Live Publisher", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        publisher.publish("lab/vision/source_status", "offline", retain=True)
        publisher.publish("lab/vision/status", "offline", retain=True)
        if cap is not None:
            cap.release()
        if args.display:
            cv2.destroyAllWindows()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
