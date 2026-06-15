"""Offline people-only YOLO model comparison. Never connects to MQTT or controls relays."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import Counter
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO


def load_zones(path: Path) -> list[list[tuple[int, int]]]:
    data = json.loads(path.read_text())
    return [[tuple(point) for point in polygon] for polygon in data["zones"]]


def point_in_polygon(point: tuple[int, int], polygon: list[tuple[int, int]]) -> bool:
    return cv2.pointPolygonTest(__import__("numpy").array(polygon), point, False) >= 0


def assigned_zone(point: tuple[int, int], zones: list[list[tuple[int, int]]]) -> int | None:
    matches = [index + 1 for index, polygon in enumerate(zones) if point_in_polygon(point, polygon)]
    return matches[0] if len(matches) == 1 else None


def summarize(rows: list[dict], elapsed: float, peak_gpu_mb: float, source_fps: float) -> dict:
    counts = [row["people_count"] for row in rows]
    track_ids = [track_id for row in rows for track_id in row["track_ids"]]
    count_changes = sum(left != right for left, right in zip(counts, counts[1:]))
    zone_changes = sum(left["zone_counts"] != right["zone_counts"] for left, right in zip(rows, rows[1:]))
    visible_tracks = Counter(track_ids)
    short_tracks = sum(length < max(3, round(source_fps / 2)) for length in visible_tracks.values())
    return {
        "frames": len(rows),
        "average_fps": len(rows) / elapsed if elapsed else 0,
        "average_inference_ms": statistics.mean(row["inference_ms"] for row in rows),
        "p95_inference_ms": sorted(row["inference_ms"] for row in rows)[max(0, int(len(rows) * 0.95) - 1)],
        "peak_gpu_memory_mb": peak_gpu_mb,
        "mean_people_count": statistics.mean(counts),
        "max_people_count": max(counts),
        "count_changes": count_changes,
        "zone_count_changes": zone_changes,
        "unique_track_ids": len(visible_tracks),
        "short_lived_track_ids": short_tracks,
        "unassigned_detections": sum(row["unassigned"] for row in rows),
        "class_filter": [0],
    }


def compare_model(model_path: Path, source: Path, output_dir: Path, zones_path: Path, conf: float, imgsz: int,
                  device: int, tracker: str, max_frames: int | None) -> dict:
    zones = load_zones(zones_path)
    model = YOLO(str(model_path))
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {source}")
    source_fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    stem = model_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_dir / f"{stem}_annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"),
                             source_fps, (width, height))
    rows = []
    cuda_device = torch.device(f"cuda:{device}")
    torch.cuda.set_device(device)
    torch.cuda.empty_cache()
    try:
        torch.cuda.reset_peak_memory_stats()
    except RuntimeError:
        pass
    start = time.perf_counter()
    frame_index = 0
    while max_frames is None or frame_index < max_frames:
        ok, frame = capture.read()
        if not ok:
            break
        tick = time.perf_counter()
        result = model.track(frame, persist=True, classes=[0], conf=conf, imgsz=imgsz, device=device,
                             tracker=tracker, verbose=False)[0]
        torch.cuda.synchronize(cuda_device)
        inference_ms = (time.perf_counter() - tick) * 1000
        zone_counts = [0] * 6
        track_ids, detections, unassigned = [], [], 0
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().tolist()
            ids = result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [-1] * len(boxes)
            confidences = result.boxes.conf.cpu().tolist()
            for box, track_id, confidence in zip(boxes, ids, confidences):
                x1, y1, x2, y2 = map(int, box)
                point = ((x1 + x2) // 2, y2)
                zone = assigned_zone(point, zones)
                if zone is None:
                    unassigned += 1
                else:
                    zone_counts[zone - 1] += 1
                track_ids.append(track_id)
                detections.append({"box": [x1, y1, x2, y2], "confidence": round(confidence, 5),
                                   "track_id": track_id, "bottom_center": point, "zone": zone})
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, point, 4, (0, 255, 255), -1)
                cv2.putText(frame, f"person #{track_id} z{zone or '-'} {confidence:.2f}", (x1, max(20, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        for index, polygon in enumerate(zones):
            cv2.polylines(frame, [__import__("numpy").array(polygon)], True, (255, 128, 0), 2)
            cv2.putText(frame, f"Z{index + 1}:{zone_counts[index]}", polygon[0], cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (255, 128, 0), 2, cv2.LINE_AA)
        writer.write(frame)
        rows.append({"frame": frame_index, "time_seconds": frame_index / source_fps, "people_count": len(detections),
                     "zone_counts": zone_counts, "track_ids": track_ids, "unassigned": unassigned,
                     "inference_ms": inference_ms, "detections": detections})
        frame_index += 1
    elapsed = time.perf_counter() - start
    capture.release()
    writer.release()
    try:
        peak_gpu_mb = torch.cuda.max_memory_allocated() / 1024**2
    except RuntimeError:
        peak_gpu_mb = 0.0
    summary = summarize(rows, elapsed, peak_gpu_mb, source_fps)
    summary.update({"model": str(model_path), "source": str(source), "confidence": conf, "imgsz": imgsz,
                    "device": f"cuda:{device}", "tracker": tracker, "people_only_class_id": 0})
    (output_dir / f"{stem}_summary.json").write_text(json.dumps(summary, indent=2))
    with (output_dir / f"{stem}_frames.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    with (output_dir / f"{stem}_frames.csv").open("w", newline="") as handle:
        writer_csv = csv.DictWriter(handle, fieldnames=["frame", "time_seconds", "people_count", "zone_counts",
                                                        "track_ids", "unassigned", "inference_ms"])
        writer_csv.writeheader()
        for row in rows:
            writer_csv.writerow({key: row[key] for key in writer_csv.fieldnames})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--zones", default="config/zones.json")
    parser.add_argument("--output", default="comparison-results")
    parser.add_argument("--conf", type=float, default=0.35)
    parser.add_argument("--imgsz", type=int, default=1280)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--tracker", default="bytetrack.yaml")
    parser.add_argument("--max-frames", type=int)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for this comparison")
    summaries = [compare_model(Path(model), Path(args.source), Path(args.output), Path(args.zones), args.conf,
                               args.imgsz, args.device, args.tracker, args.max_frames) for model in args.models]
    Path(args.output, "comparison-summary.json").write_text(json.dumps(summaries, indent=2))
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
