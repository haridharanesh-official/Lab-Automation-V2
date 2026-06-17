from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2


REPO_ROOT = Path(__file__).resolve().parents[2]
AI_PC_ROOT = REPO_ROOT / "ai-pc"
if str(AI_PC_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_PC_ROOT))

from src.main import CountWindow  # noqa: E402
from src.main import draw_detection_overlay  # noqa: E402
from src.main import frame_assignments  # noqa: E402
from src.main import load_config  # noqa: E402
from src.main import load_zones  # noqa: E402
from src.zones import assign_zone  # noqa: E402


OUTSIDE_ZONE = "OUTSIDE_ZONE"


def parse_point(value: str) -> tuple[int, int]:
    parts = value.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("point must be formatted as x,y")
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("point coordinates must be integers") from exc


def zone_label(zone: int | None) -> str:
    return f"Zone {zone}" if zone is not None else OUTSIDE_ZONE


def assign_point(point: tuple[int, int], zones_path: str) -> int | None:
    return assign_zone(point, load_zones(zones_path))


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def summarize_observations(observations: list[dict[str, Any]]) -> dict[str, Any]:
    marked = [row for row in observations if row.get("expected_zone") is not None]
    matches = [row for row in marked if row.get("expected_zone") == row.get("observed_zone")]
    mismatches = [row for row in marked if row.get("expected_zone") != row.get("observed_zone")]
    observed_counts = Counter(row.get("observed_zone") for row in observations)
    expected_counts = Counter(row.get("expected_zone") for row in marked)
    return {
        "total_observations": len(observations),
        "marked_observations": len(marked),
        "matches": len(matches),
        "mismatches": len(mismatches),
        "expected_counts": {str(key): value for key, value in sorted(expected_counts.items())},
        "observed_counts": {str(key): value for key, value in sorted(observed_counts.items(), key=lambda item: str(item[0]))},
        "mismatch_rows": mismatches,
    }


def write_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def append_csv(path: Path, row: dict[str, Any]) -> None:
    fieldnames = [
        "timestamp",
        "frame",
        "event",
        "expected_zone",
        "observed_zone",
        "current_zone_counts",
        "stable_zone_counts",
        "person_count",
        "snapshot",
    ]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow({key: row.get(key) for key in fieldnames})


def build_observation(
    event: str,
    frame_index: int,
    expected_zone: int | None,
    current_zone_counts: list[int],
    stable_zone_counts: list[int],
    assignments: list[dict[str, Any]],
    snapshot: str | None = None,
) -> dict[str, Any]:
    observed_zone = None
    if expected_zone is not None:
        zones_present = [assignment.get("zone") for assignment in assignments if assignment.get("zone") is not None]
        observed_zone = expected_zone if expected_zone in zones_present else (zones_present[0] if zones_present else None)
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "frame": frame_index,
        "event": event,
        "expected_zone": expected_zone,
        "observed_zone": observed_zone,
        "current_zone_counts": list(current_zone_counts),
        "stable_zone_counts": list(stable_zone_counts),
        "person_count": sum(current_zone_counts),
        "assignments": assignments,
        "snapshot": snapshot,
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("\nZone walk summary")
    print(f"  total observations: {summary['total_observations']}")
    print(f"  marked observations: {summary['marked_observations']}")
    print(f"  matches: {summary['matches']}")
    print(f"  mismatches: {summary['mismatches']}")
    print(f"  expected counts: {summary['expected_counts']}")
    print(f"  observed counts: {summary['observed_counts']}")
    if summary["mismatch_rows"]:
        print("  mismatch rows:")
        for row in summary["mismatch_rows"]:
            print(
                f"    frame {row['frame']}: expected Z{row['expected_zone']} "
                f"observed {zone_label(row['observed_zone'])}"
            )


def run_point_mode(args: argparse.Namespace) -> int:
    zone = assign_point(args.point, args.zones)
    print(f"{args.point[0]},{args.point[1]} -> {zone_label(zone)}")
    return 0


def run_live(args: argparse.Namespace) -> int:
    from ultralytics import YOLO

    config = load_config(args.config)
    camera = config["camera"]
    model_config = config["model"]
    zones = load_zones(args.zones or config.get("zones_path", "config/zones.json"))
    output_dir = ensure_output_dir(Path(args.output_dir) / timestamp_slug())
    jsonl_path = output_dir / "observations.jsonl"
    csv_path = output_dir / "observations.csv"
    summary_path = output_dir / "summary.json"

    model = YOLO(args.model or model_config["path"])
    cap = cv2.VideoCapture(args.source or camera["url"], cv2.CAP_FFMPEG)
    if not cap.isOpened():
        raise SystemExit(f"could not open RTSP stream: {args.source or camera['url']}")

    window = CountWindow(window_seconds=float(args.window_seconds or config.get("report_seconds", 60)))
    observations: list[dict[str, Any]] = []
    frame_index = 0
    last_frame_time = time.monotonic()
    started = last_frame_time
    last_annotated = None

    print("Zone walk test controls: 1-6 mark expected zone, s saves snapshot, q quits")
    print(f"Writing observations to {output_dir}")

    try:
        while True:
            if args.duration and time.monotonic() - started >= args.duration:
                break
            ok, frame = cap.read()
            if not ok:
                print("camera read failed; stopping without publishing anything")
                break
            frame_index += 1
            now = time.monotonic()
            fps = 1 / (now - last_frame_time) if now > last_frame_time else 0.0
            last_frame_time = now
            tick = time.perf_counter()
            result = model.track(
                frame,
                persist=True,
                classes=[0],
                conf=float(args.confidence or model_config["confidence"]),
                imgsz=int(args.image_size or model_config["image_size"]),
                device=args.device if args.device is not None else model_config["device"],
                tracker=args.tracker or model_config["tracker"],
                verbose=False,
            )[0]
            latency_ms = (time.perf_counter() - tick) * 1000
            current_zone_counts, assignments = frame_assignments(result, zones)
            window.add(current_zone_counts, sample_time=now)
            stable_zone_counts = window.medians(now)
            annotated = frame.copy()
            draw_detection_overlay(
                annotated,
                assignments,
                zones,
                current_zone_counts,
                stable_zone_counts,
                sum(stable_zone_counts),
                fps,
                latency_ms,
                "healthy",
                window.sample_count(),
                window.seconds_until_report(now),
                stable_zone_counts,
            )
            cv2.putText(
                annotated,
                "Zone walk: press 1-6 expected zone, s snapshot, q quit",
                (20, annotated.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            last_annotated = annotated
            cv2.imshow("Lab Automation Zone Walk Test", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                snapshot_path = output_dir / f"snapshot-frame-{frame_index:06d}.jpg"
                cv2.imwrite(str(snapshot_path), annotated)
                row = build_observation(
                    "snapshot",
                    frame_index,
                    None,
                    current_zone_counts,
                    stable_zone_counts,
                    assignments,
                    str(snapshot_path),
                )
                observations.append(row)
                write_jsonl(jsonl_path, row)
                append_csv(csv_path, row)
                print(f"saved snapshot: {snapshot_path}")
            if ord("1") <= key <= ord("6"):
                expected_zone = int(chr(key))
                snapshot_path = output_dir / f"expected-z{expected_zone}-frame-{frame_index:06d}.jpg"
                cv2.imwrite(str(snapshot_path), annotated)
                row = build_observation(
                    "expected_zone",
                    frame_index,
                    expected_zone,
                    current_zone_counts,
                    stable_zone_counts,
                    assignments,
                    str(snapshot_path),
                )
                observations.append(row)
                write_jsonl(jsonl_path, row)
                append_csv(csv_path, row)
                print(
                    f"marked expected Z{expected_zone}: observed {zone_label(row['observed_zone'])}, "
                    f"counts={current_zone_counts}"
                )
    finally:
        cap.release()
        cv2.destroyAllWindows()

    if not observations and last_annotated is not None:
        snapshot_path = output_dir / f"final-frame-{frame_index:06d}.jpg"
        cv2.imwrite(str(snapshot_path), last_annotated)
    summary = summarize_observations(observations)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print_summary(summary)
    print(f"Summary saved to {summary_path}")
    return 0 if summary["mismatches"] == 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live zone-by-zone walk validation helper.")
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--zones", default="config/zones.json")
    parser.add_argument("--point", type=parse_point, help="non-live test point formatted as x,y")
    parser.add_argument("--source", help="override RTSP source")
    parser.add_argument("--model", help="override YOLO model path")
    parser.add_argument("--confidence", type=float)
    parser.add_argument("--image-size", type=int)
    parser.add_argument("--device")
    parser.add_argument("--tracker")
    parser.add_argument("--window-seconds", type=float)
    parser.add_argument("--duration", type=float, default=0, help="optional live duration in seconds")
    parser.add_argument("--output-dir", default="monitor-results/zone-walk")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.point is not None:
        return run_point_mode(args)
    return run_live(args)


if __name__ == "__main__":
    raise SystemExit(main())
