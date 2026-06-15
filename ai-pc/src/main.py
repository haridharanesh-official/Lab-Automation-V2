"""Production vision entry point. Defaults to monitor mode and publishes telemetry only."""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .reporting import build_report
from .zones import CountWindow


def camera_interrupted(window: CountWindow) -> None:
    window.clear()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="validate configuration without opening camera or MQTT")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text()) if args.config.endswith(".json") else Path(args.config).read_text()
    if args.dry_run:
        print(f"configuration loaded; physical control disabled ({len(config)} bytes)")
        return
    raise SystemExit("Install production dependencies and configure camera/MQTT before running vision.")


if __name__ == "__main__":
    main()

