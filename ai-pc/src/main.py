"""Production vision entry point. Defaults to monitor mode and publishes telemetry only."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import cv2
import paho.mqtt.client as mqtt
import yaml
from ultralytics import YOLO

from .mqtt_publisher import VisionPublisher
from .reporting import build_report
from .zones import CountWindow
from .zones import assign_zone


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


def counts_from_frame(result, zones: list[list[tuple[int, int]]]) -> list[int]:
    counts = [0] * 6
    if result.boxes is None:
        return counts
    for raw_box in result.boxes.xyxy.cpu().tolist():
        box = [int(round(value)) for value in raw_box]
        bottom_center = ((box[0] + box[2]) // 2, box[3])
        zone = assign_zone(bottom_center, zones)
        if zone is not None and 1 <= zone <= 6:
            counts[zone - 1] += 1
    return counts


def publish_status(publisher: VisionPublisher, source_status: str, stable_count: int, zone_counts: list[int],
                   frame_fps: float, latency_ms: float) -> None:
    now_ms = int(time.time() * 1000)
    publisher.publish("lab/vision/status", "online", retain=True)
    publisher.publish("lab/vision/source_status", source_status, retain=True)
    publisher.publish(
        "lab/vision/people_count",
        {
            "publisher": "labvision-ai-pc",
            "timestamp": now_ms,
            "total_count": sum(zone_counts),
            "stable_count": stable_count,
            "zone_counts": zone_counts,
            "source_healthy": source_status == "healthy",
            "status": "online",
            "fps": round(frame_fps, 3),
            "inference_ms": round(latency_ms, 3),
        },
        retain=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="validate configuration without opening camera or MQTT")
    parser.add_argument("--duration", type=float, default=0, help="optional runtime limit in seconds; 0 means run until stopped")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.dry_run:
        print(json.dumps(config, indent=2))
        return

    if str(config.get("mode", "monitor")).lower() != "monitor":
        raise SystemExit("vision runtime refuses non-monitor mode")

    mqtt_config = config.get("mqtt", {})
    if not mqtt_config.get("enabled", False):
        raise SystemExit("mqtt.enabled must be true for live publisher mode")

    camera = config["camera"]
    model_config = config["model"]
    zones = load_zones(config.get("zones_path", "config/zones.json"))
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
    window = CountWindow()
    last_heartbeat = 0.0
    last_publish = 0.0
    started = time.monotonic()
    last_frame_time = started

    try:
        while True:
            if args.duration and time.monotonic() - started >= args.duration:
                break
            if cap is None:
                cap = cv2.VideoCapture(camera["url"], cv2.CAP_FFMPEG)
                if not cap.isOpened():
                    publisher.publish("lab/vision/source_status", "unhealthy", retain=True)
                    time.sleep(float(camera.get("reconnect_seconds", 5)))
                    continue
                publisher.publish("lab/vision/source_status", "healthy", retain=True)
            ok, frame = cap.read()
            if not ok:
                publisher.publish("lab/vision/source_status", "unhealthy", retain=True)
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
            zone_counts = counts_from_frame(result, zones)
            window.add(zone_counts)
            stable_zone_counts = window.medians()
            stable_count = sum(stable_zone_counts)

            if now - last_publish >= 1.0:
                publish_status(publisher, "healthy", stable_count, stable_zone_counts, frame_fps, latency_ms)
                last_publish = now
            if now - last_heartbeat >= float(config.get("heartbeat_seconds", 10)):
                publisher.publish(
                    "lab/vision/heartbeat",
                    {"publisher": "labvision-ai-pc", "timestamp": int(time.time()), "status": "online"},
                    retain=False,
                )
                last_heartbeat = now
    finally:
        publisher.publish("lab/vision/source_status", "offline", retain=True)
        publisher.publish("lab/vision/status", "offline", retain=True)
        if cap is not None:
            cap.release()
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
