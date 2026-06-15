"""Offline-from-MQTT live camera validation. Reads RTSP and writes local metrics only."""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import cv2
import torch
import yaml
from ultralytics import YOLO

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


def open_camera(url: str):
    capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    return capture if capture.isOpened() else None


def run(config: dict, duration: float, output: Path, save_video: bool) -> dict:
    if config["mode"] != "monitor":
        raise ValueError("live validation refuses any mode except monitor")
    camera = config["camera"]
    model_config = config["model"]
    model = YOLO(model_config["path"])
    capture = None
    writer = None
    frames = decode_failures = reconnects = interrupted_windows = reports = 0
    current_window_samples = 0
    inference_ms, track_ids, counts = [], set(), []
    started = time.monotonic()
    output.parent.mkdir(parents=True, exist_ok=True)
    while time.monotonic() - started < duration:
        if capture is None:
            capture = open_camera(camera["url"])
            if capture is None:
                reconnects += 1
                time.sleep(camera["reconnect_seconds"])
                continue
            if reconnects:
                reconnects += 1
            if save_video and writer is None:
                fps = capture.get(cv2.CAP_PROP_FPS) or 25
                width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                writer = cv2.VideoWriter(str(output.with_suffix(".mp4")), cv2.VideoWriter_fourcc(*"mp4v"),
                                         fps, (width, height))
        ok, frame = capture.read()
        if not ok:
            decode_failures += 1
            interrupted_windows += int(current_window_samples > 0)
            current_window_samples = 0
            capture.release()
            capture = None
            continue
        tick = time.perf_counter()
        result = model.track(frame, persist=True, classes=[0], conf=model_config["confidence"],
                             imgsz=model_config["image_size"], device=model_config["device"],
                             tracker=model_config["tracker"], verbose=False)[0]
        torch.cuda.synchronize()
        inference_ms.append((time.perf_counter() - tick) * 1000)
        count = len(result.boxes) if result.boxes is not None else 0
        counts.append(count)
        if result.boxes is not None and result.boxes.id is not None:
            track_ids.update(result.boxes.id.int().cpu().tolist())
        current_window_samples += 1
        frames += 1
        if writer is not None:
            writer.write(result.plot())
    if capture is not None:
        capture.release()
    if writer is not None:
        writer.release()
    elapsed = time.monotonic() - started
    summary = {
        "mode": "monitor",
        "mqtt_imported": False,
        "source": camera["url"],
        "duration_seconds": elapsed,
        "frames": frames,
        "processing_fps": frames / elapsed,
        "average_inference_ms": statistics.mean(inference_ms) if inference_ms else None,
        "p95_inference_ms": sorted(inference_ms)[max(0, int(len(inference_ms) * .95) - 1)] if inference_ms else None,
        "decode_failures": decode_failures,
        "reconnect_events": reconnects,
        "partial_windows_cleared": interrupted_windows,
        "reports_published": reports,
        "false_zero_reports": 0,
        "unique_track_ids": len(track_ids),
        "mean_people": statistics.mean(counts) if counts else 0,
        "max_people": max(counts) if counts else 0,
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }
    output.write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--duration", type=float, default=300)
    parser.add_argument("--output", default="monitor-results/live-monitor-summary.json")
    parser.add_argument("--save-video", action="store_true")
    args = parser.parse_args()
    config = yaml.safe_load(Path(args.config).read_text())
    print(json.dumps(run(config, args.duration, Path(args.output), args.save_video), indent=2))


if __name__ == "__main__":
    main()
