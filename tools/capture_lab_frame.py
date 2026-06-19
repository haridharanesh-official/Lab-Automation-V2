"""Capture a lab camera frame for zone calibration.

This tool only reads an RTSP stream or image source and writes an image file.
It does not publish MQTT, change modes, or touch relay topics.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import cv2


DEFAULT_RTSP = "rtsp://hari:8554/labcam"


def capture_frame(rtsp_url: str, output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(rtsp_url)
    try:
        if not capture.isOpened():
            raise RuntimeError(f"could not open RTSP stream: {rtsp_url}")
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError("RTSP stream opened but no frame was returned")
        if not cv2.imwrite(str(output_path), frame):
            raise RuntimeError(f"could not write frame to {output_path}")
        return output_path
    finally:
        capture.release()


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture one frame from the lab RTSP camera.")
    parser.add_argument("--rtsp", default=DEFAULT_RTSP)
    parser.add_argument(
        "--output",
        default=f"monitor-results/zone-calibration/labcam-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jpg",
    )
    args = parser.parse_args()
    path = capture_frame(args.rtsp, args.output)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
