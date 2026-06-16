"""Live people-only model validation for RTSP camera streams.

This script reads a camera stream and writes local validation artifacts only.
It does not import MQTT clients, publish topics, deploy flows, or control relays.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


def load_zones(path: Path) -> list[list[tuple[int, int]]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return [[tuple(point) for point in polygon] for polygon in data.get("zones", [])]


def assigned_zone(point: tuple[int, int], zones: list[list[tuple[int, int]]]) -> int | None:
    matches = [index + 1 for index, polygon in enumerate(zones) if cv2.pointPolygonTest(np.array(polygon), point, False) >= 0]
    return matches[0] if len(matches) == 1 else None


def box_iou(left: list[int], right: list[int]) -> float:
    left_x1, left_y1, left_x2, left_y2 = left
    right_x1, right_y1, right_x2, right_y2 = right
    inter_x1 = max(left_x1, right_x1)
    inter_y1 = max(left_y1, right_y1)
    inter_x2 = min(left_x2, right_x2)
    inter_y2 = min(left_y2, right_y2)
    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    left_area = max(0, left_x2 - left_x1) * max(0, left_y2 - left_y1)
    right_area = max(0, right_x2 - right_x1) * max(0, right_y2 - right_y1)
    union = left_area + right_area - inter_area
    return inter_area / union if union else 0.0


def duplicate_warnings(boxes: list[list[int]], threshold: float) -> list[dict]:
    warnings = []
    for left_index, left_box in enumerate(boxes):
        for right_index in range(left_index + 1, len(boxes)):
            overlap = box_iou(left_box, boxes[right_index])
            if overlap >= threshold:
                warnings.append(
                    {
                        "left_index": left_index,
                        "right_index": right_index,
                        "iou": round(overlap, 5),
                        "threshold": threshold,
                    }
                )
    return warnings


def zone_boundary_uncertain(point: tuple[int, int], zones: list[list[tuple[int, int]]], threshold_px: float) -> bool:
    if not zones:
        return False
    distances = [abs(cv2.pointPolygonTest(np.array(polygon), point, True)) for polygon in zones]
    return min(distances) <= threshold_px


def draw_overlay(frame, detections: list[dict], zones: list[list[tuple[int, int]]], frame_fps: float, latency_ms: float) -> None:
    zone_counts = [0] * len(zones)
    for detection in detections:
        zone = detection["zone"]
        if zone is not None and 1 <= zone <= len(zone_counts):
            zone_counts[zone - 1] += 1
        x1, y1, x2, y2 = detection["box"]
        label = f"person {detection['confidence']:.2f} z:{zone or '-'}"
        if detection["track_id"] is not None:
            label += f" id:{detection['track_id']}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, tuple(detection["bottom_center"]), 4, (0, 255, 255), -1)
        cv2.putText(frame, label, (x1, max(20, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
    for index, polygon in enumerate(zones):
        cv2.polylines(frame, [np.array(polygon)], True, (255, 128, 0), 2)
        cv2.putText(frame, f"Z{index + 1}:{zone_counts[index]}", polygon[0], cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 128, 0), 2, cv2.LINE_AA)
    total = len(detections)
    cv2.rectangle(frame, (0, 0), (430, 64), (0, 0, 0), -1)
    cv2.putText(frame, f"People: {total} | FPS: {frame_fps:.1f} | Latency: {latency_ms:.1f} ms", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(frame, "Monitor validation only - MQTT disabled - relay /set: 0", (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 255, 180), 1, cv2.LINE_AA)


def open_capture(url: str):
    capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    return capture if capture.isOpened() else None


def run(args: argparse.Namespace) -> dict:
    zones = load_zones(Path(args.zones))
    model = YOLO(args.model)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "live-model-validation-summary.json"
    csv_path = output_dir / "live-model-validation-frames.csv"
    jsonl_path = output_dir / "live-model-validation-frames.jsonl"
    video_path = output_dir / "live-model-validation-annotated.mp4"

    if torch.cuda.is_available() and str(args.device) != "cpu":
        torch.cuda.set_device(int(args.device))
        torch.cuda.empty_cache()
        try:
            torch.cuda.reset_peak_memory_stats(int(args.device))
        except RuntimeError:
            pass

    capture = None
    writer = None
    rows = []
    latencies = []
    counts = []
    decode_failures = 0
    reconnects = 0
    false_zero_events = 0
    previous_positive = False
    frame_number = 0
    started = time.monotonic()
    last_frame_time = started
    with csv_path.open("w", newline="", encoding="utf-8") as csv_handle, jsonl_path.open("w", encoding="utf-8") as jsonl_handle:
        fieldnames = [
            "frame",
            "timestamp_seconds",
            "fps",
            "inference_latency_ms",
            "person_count",
            "confidence_values",
            "boxes",
            "duplicate_warnings",
            "zone_assignments",
            "zone_counts",
            "zone_boundary_uncertain",
        ]
        writer_csv = csv.DictWriter(csv_handle, fieldnames=fieldnames)
        writer_csv.writeheader()
        while time.monotonic() - started < args.duration:
            if capture is None:
                capture = open_capture(args.source)
                if capture is None:
                    reconnects += 1
                    time.sleep(args.reconnect_seconds)
                    continue
                if reconnects:
                    reconnects += 1
                if writer is None:
                    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
                    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
                    source_fps = capture.get(cv2.CAP_PROP_FPS) or 25
                    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), source_fps, (width, height))
            ok, frame = capture.read()
            if not ok:
                decode_failures += 1
                capture.release()
                capture = None
                continue

            now = time.monotonic()
            frame_fps = 1 / (now - last_frame_time) if now > last_frame_time else 0
            last_frame_time = now
            tick = time.perf_counter()
            result = model.track(
                frame,
                persist=True,
                classes=[0],
                conf=args.confidence,
                imgsz=args.image_size,
                device=args.device,
                tracker=args.tracker,
                verbose=False,
            )[0]
            if torch.cuda.is_available() and str(args.device) != "cpu":
                torch.cuda.synchronize(int(args.device))
            latency_ms = (time.perf_counter() - tick) * 1000
            detections = []
            boxes = []
            if result.boxes is not None:
                raw_boxes = result.boxes.xyxy.cpu().tolist()
                confidences = result.boxes.conf.cpu().tolist()
                track_ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None] * len(raw_boxes)
                for raw_box, confidence, track_id in zip(raw_boxes, confidences, track_ids):
                    box = [int(round(value)) for value in raw_box]
                    boxes.append(box)
                    bottom_center = [(box[0] + box[2]) // 2, box[3]]
                    zone = assigned_zone(tuple(bottom_center), zones)
                    detections.append(
                        {
                            "box": box,
                            "confidence": round(float(confidence), 5),
                            "track_id": track_id,
                            "bottom_center": bottom_center,
                            "zone": zone,
                            "zone_boundary_uncertain": zone_boundary_uncertain(tuple(bottom_center), zones, args.zone_boundary_threshold),
                        }
                    )
            duplicates = duplicate_warnings(boxes, args.duplicate_iou)
            zone_counts = [sum(1 for detection in detections if detection["zone"] == zone) for zone in range(1, len(zones) + 1)]
            count = len(detections)
            if count == 0 and previous_positive:
                false_zero_events += 1
            previous_positive = count > 0
            row = {
                "frame": frame_number,
                "timestamp_seconds": round(time.monotonic() - started, 3),
                "fps": round(frame_fps, 3),
                "inference_latency_ms": round(latency_ms, 3),
                "person_count": count,
                "confidence_values": [detection["confidence"] for detection in detections],
                "boxes": boxes,
                "duplicate_warnings": duplicates,
                "zone_assignments": [detection["zone"] for detection in detections],
                "zone_counts": zone_counts,
                "zone_boundary_uncertain": any(detection["zone_boundary_uncertain"] for detection in detections),
            }
            writer_csv.writerow({key: json.dumps(value) if isinstance(value, (list, dict, bool)) else value for key, value in row.items()})
            jsonl_handle.write(json.dumps({**row, "detections": detections}) + "\n")
            rows.append(row)
            latencies.append(latency_ms)
            counts.append(count)
            draw_overlay(frame, detections, zones, frame_fps, latency_ms)
            writer.write(frame)
            if args.display:
                cv2.imshow(args.window_title, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            frame_number += 1

    if capture is not None:
        capture.release()
    if writer is not None:
        writer.release()
    if args.display:
        cv2.destroyAllWindows()

    elapsed = time.monotonic() - started
    duplicate_frames = sum(1 for row in rows if row["duplicate_warnings"])
    uncertain_frames = sum(1 for row in rows if row["zone_boundary_uncertain"])
    peak_gpu_memory_mb = 0.0
    if torch.cuda.is_available() and str(args.device) != "cpu":
        try:
            peak_gpu_memory_mb = torch.cuda.max_memory_allocated(int(args.device)) / 1024**2
        except RuntimeError:
            peak_gpu_memory_mb = 0.0
    summary = {
        "scope": "live AI vision validation only",
        "mqtt_enabled": False,
        "relay_set_commands_published": 0,
        "source": args.source,
        "model": args.model,
        "confidence": args.confidence,
        "image_size": args.image_size,
        "device": f"cuda:{args.device}" if str(args.device).isdigit() else args.device,
        "tracker": args.tracker,
        "class_filter": [0],
        "duration_seconds": elapsed,
        "frames": len(rows),
        "average_fps": len(rows) / elapsed if elapsed else 0,
        "average_inference_latency_ms": statistics.mean(latencies) if latencies else None,
        "p95_inference_latency_ms": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else None,
        "peak_gpu_memory_mb": peak_gpu_memory_mb,
        "decode_failures": decode_failures,
        "reconnects": reconnects,
        "frames_with_people": sum(count > 0 for count in counts),
        "frames_with_2plus_people": sum(count >= 2 for count in counts),
        "maximum_people_detected": max(counts) if counts else 0,
        "duplicate_frames": duplicate_frames,
        "duplicate_detection_rate": duplicate_frames / len(rows) if rows else 0,
        "zone_boundary_uncertain_frames": uncertain_frames,
        "zone_boundary_uncertainty_rate": uncertain_frames / len(rows) if rows else 0,
        "false_zero_events": false_zero_events,
        "annotated_video": str(video_path),
        "frames_csv": str(csv_path),
        "frames_jsonl": str(jsonl_path),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="rtsp://hari:8554/labcam")
    parser.add_argument("--model", default="models/backcam_yolov8s_improved_v3_hardfp.pt")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--image-size", type=int, default=1280)
    parser.add_argument("--device", default="0")
    parser.add_argument("--tracker", default="bytetrack.yaml")
    parser.add_argument("--zones", default="config/zones.json")
    parser.add_argument("--duration", type=float, default=600)
    parser.add_argument("--output-dir", default="monitor-results/live-model-validation")
    parser.add_argument("--reconnect-seconds", type=float, default=5)
    parser.add_argument("--duplicate-iou", type=float, default=0.70)
    parser.add_argument("--zone-boundary-threshold", type=float, default=12)
    parser.add_argument("--display", action="store_true", help="show a live OpenCV overlay window while validating")
    parser.add_argument("--window-title", default="Lab Automation v2.0 People Count")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2))


if __name__ == "__main__":
    main()
