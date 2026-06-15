# Production Readiness Report

## Validation Run: June 15, 2026

- Python: 3.11.9
- Virtual environment: `C:\Users\prith\Downloads\Lab Automation v2.0\.venv`
- GPU: NVIDIA GeForce RTX 5070
- PyTorch: 2.11.0+cu128; CUDA 12.8 available; compute capability 12.0
- Core dependencies: Ultralytics 8.4.67, OpenCV 4.13.0, Paho MQTT 2.1.0, PyYAML 6.0.3, pytest 9.1.0
- Dependency integrity: `pip check` reports no broken requirements
- Automated tests: 8 passed, 0 failed
- Offline Monitor simulator: all requested scenarios completed with 0 relay `/set` commands
- Structured artifacts: JSON and YAML parsed successfully
- Python and PowerShell syntax: passed

## Problems Found And Fixed

- Fixed editable-install failure caused by accidental setuptools discovery of non-Python top-level directories.
- Replaced CPU-only PyTorch with the official CUDA 12.8 build and verified RTX 5070 detection.
- Expanded the safe simulator to cover individual zones, multiple/all occupied, two empty reports, invalid, duplicate, out-of-order, and unavailable vision.
- Added fake-client publisher tests proving unsafe topics are rejected before any MQTT publish call.
- Ignored generated `*.egg-info/` metadata.

## Verified in Software

- Isolated v2 namespace and vision topic allowlist
- Complete report validation and sequence rejection
- Manual/Monitor command isolation
- Ten-relay mapping and fan OR rules
- Two-report empty shutdown
- Failure state preservation
- Command deduplication
- Active-LOW safe-off ESP32 initialization with GPIO 33 replacing GPIO 5

## Remaining Blockers

- Custom model and YOLO11s completed an offline comparison; custom model is recommended. Objective accuracy scoring still requires human ground-truth labels.
- Monitor runtime configuration uses the selected custom model. Both known RTSP routes failed verification on June 16, 2026, so five-minute live detection, real timing, tracking, reconnection, and final zone calibration were not run.
- Physical polygon calibration and boundary stability
- Exact report/heartbeat timing under real workload
- Broker, Node-RED, Home Assistant, and ESP32 integration
- ESP32 discovery completeness and physical relay boot behavior
- Supervised Auto-mode operation

Status: **not production-ready** until all unchecked validation items pass on the actual lab hardware.
