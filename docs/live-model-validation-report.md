# Live Model Validation Report

Date: June 16, 2026

## Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

Scope: live AI vision validation only. Auto mode, relays, ESP32 firmware, Home Assistant controls, and Node-RED deployment were not touched. MQTT publishing was disabled; no relay `/set` commands were published.

## Stream

- URL: `rtsp://hari:8554/labcam`
- Open check: passed with `ffprobe`
- Codec: HEVC/H.265
- Resolution: `1280x720`
- Nominal stream FPS: `25`

## Model Settings

- Model: `models/backcam_yolov8s_improved_v3_hardfp.pt`
- Confidence: `0.35`
- Image size: `1280`
- Device: CUDA `0`, `NVIDIA GeForce RTX 5070`
- Tracker: `bytetrack.yaml`
- Class filter: person only, class ID `0`
- Zone file: `config/zones.json`
- Duplicate-box warning threshold: IoU `0.70`

## Ten-Minute Run

Artifacts were written under ignored runtime output:

- Annotated video: `monitor-results/live-model-validation-20260616/live-model-validation-annotated.mp4`
- Per-frame CSV: `monitor-results/live-model-validation-20260616/live-model-validation-frames.csv`
- Per-frame JSONL: `monitor-results/live-model-validation-20260616/live-model-validation-frames.jsonl`
- Summary: `monitor-results/live-model-validation-20260616/live-model-validation-summary.json`

| Metric | Result |
| --- | ---: |
| Runtime | `600.0 s` |
| Frames processed | `9,832` |
| Average processing FPS | `16.39` |
| Average inference latency | `13.70 ms` |
| P95 inference latency | `18.04 ms` |
| Peak GPU memory | `188.83 MB` |
| Decode failures | `1` |
| Reconnect attempts/events | `40` |
| Frames with people | `9,753` |
| Frames with 2+ people | `9,701` |
| Maximum people detected | `7` |
| Duplicate-box frames | `9` |
| Duplicate detection rate | `0.0915%` |
| Zone-boundary uncertain frames | `5,821` |
| Zone-boundary uncertainty rate | `59.20%` |
| False-zero events | `7` |
| MQTT reports published | `0` |
| Relay `/set` commands published | `0` |

## Detection Quality Observations

The selected model continued to detect people throughout most of the run. The validation window contained mostly occupied-lab frames:

- Zero-person frames: `79`
- One-person frames: `52`
- Two-or-more-person frames: `9,701`

The run did not include controlled empty-lab, seated-only, standing-only, or occlusion-only moments. Those cases still need supervised scene staging before they can be marked physically validated.

## Duplicate-Box Findings

Duplicate-box warnings were rare: `9` of `9,832` frames had at least one pair of person boxes with IoU at or above `0.70`. This is not a dominant issue in the run, but the affected frames should be reviewed in the annotated video before enabling any hardware automation.

## False-Positive And False-Zero Findings

The live run observed `7` false-zero transitions, defined as a zero-person frame immediately following a positive frame. The most likely cause is stream instability during reconnect periods, not a sustained empty-lab model decision. Because the lab was not held empty for a controlled interval, false positives on empty scenes were not fully measurable.

## Zone Assignment Findings

Zone assignment used the bottom-centre of each person bounding box. Aggregate provisional zone totals were:

- Zone 1: `11,542`
- Zone 2: `14,425`
- Zone 3: `35`
- Zone 4: `190`
- Zone 5: `56`
- Zone 6: `49`

The current six-zone configuration remains provisional. `59.20%` of frames had at least one detection near a zone boundary using the current `12 px` uncertainty threshold, so final zone calibration is still required before supervised Auto-mode testing.

## Stream Stability Finding

The AI validator completed the full ten-minute runtime, but the stream was not continuously stable. During the run, OpenCV/FFmpeg saw repeated RTSP `404 Not Found` responses and recovered after reconnect attempts. A post-run check on `hari` showed `labos-camera-bridge.service` had restarted during the validation window and MediaMTX later reported `/labcam` online again.

This means live vision can run, but camera bridge stability remains a deployment blocker.

## Readiness Result

The model is acceptable for continued Monitor-mode testing, but the system is not physically production-ready. Before supervised relay validation or Auto mode, complete:

- Camera bridge hardening so upstream interruptions do not expose intermittent `/labcam` `404` periods.
- Controlled live scene tests for one standing person, one seated person, multiple people, partial occlusion, and empty lab/chairs-only.
- Final zone calibration against real room boundaries.
- Supervised relay, ESP32, Node-RED, Home Assistant, Auto-mode, and failure validation.
