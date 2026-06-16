# Live People-Count Validation

Date: June 16, 2026

## Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

Scope: live camera and AI model only. Auto mode, ESP32 firmware, physical relays, Home Assistant controls, and Node-RED deployment were not touched. Earlier validation runs used MQTT disabled and published no relay `/set` commands.

Deployment update: the current `labos` Raspberry Pi runtime consumes `lab/vision/...` topics rather than the earlier repo draft `labos/v2/vision/...` namespace. The AI PC publisher is now aligned to publish only `lab/vision/people_count`, `lab/vision/status`, `lab/vision/source_status`, and `lab/vision/heartbeat`, while still refusing all relay/control/set/command topics.

## Settings

- Stream: `rtsp://hari:8554/labcam`
- Model: `models/backcam_yolov8s_improved_v3_hardfp.pt`
- Confidence: `0.35`
- Image size: `1280`
- Device: CUDA `0`, `NVIDIA GeForce RTX 5070`
- Tracker: `bytetrack.yaml`
- Class filter: person only, class ID `0`
- Zone assignment: bottom-centre of each bounding box using `config/zones.json`
- Display: live overlay window with bounding boxes, track IDs, total count, six zone counts, FPS, and inference latency

## Artifacts

Runtime artifacts were written under ignored output:

- Annotated video: `monitor-results/live-people-count-validation-20260616/live-model-validation-annotated.mp4`
- Per-frame CSV: `monitor-results/live-people-count-validation-20260616/live-model-validation-frames.csv`
- Per-frame JSONL: `monitor-results/live-people-count-validation-20260616/live-model-validation-frames.jsonl`
- Summary: `monitor-results/live-people-count-validation-20260616/live-model-validation-summary.json`

## Metrics

| Metric | Result |
| --- | ---: |
| Runtime | `600.015 s` |
| Frames processed | `14,984` |
| Average FPS | `24.97` |
| Average inference latency | `13.76 ms` |
| P95 inference latency | `17.95 ms` |
| Peak GPU memory | `188.83 MB` |
| Decode failures | `0` |
| Reconnects | `0` |
| Frames with people | `14,968` |
| Frames with 2+ people | `14,668` |
| Maximum people detected | `6` |
| Duplicate-box frames | `53` |
| Duplicate detection rate | `0.354%` |
| Zone-boundary uncertain frames | `5,442` |
| Zone-boundary uncertainty rate | `36.32%` |
| False-zero events | `0` |
| MQTT reports published | `0` |
| Relay `/set` commands published | `0` |

## Count Observations

The overlay showed stable people tracking through the validation window. The logged frame distribution was:

- Zero-person frames: `16`
- One-person frames: `300`
- Two-or-more-person frames: `14,668`

People-count accuracy looked suitable for continued Monitor-mode testing, but it was not a controlled ground-truth audit. The run did not include deliberately staged moments for a single standing person, a seated-only person, partial occlusion, or a sustained empty-lab/chairs-only scene. Those must still be validated with a human observer before any physical Auto-mode use.

## Duplicate And False-Zero Findings

Duplicate boxes were rare but present: `53` frames had at least one duplicate-box warning at IoU `0.70`, a `0.354%` frame rate. No false-zero events occurred during this run, and brief camera glitches did not produce zero-count transitions because there were no decode failures or reconnects.

## Zone Findings

Aggregate provisional zone totals:

- Zone 1: `3,528`
- Zone 2: `26,402`
- Zone 3: `0`
- Zone 4: `11,601`
- Zone 5: `83`
- Zone 6: `95`

Zone assignment was reasonable as a software exercise, but the current polygons remain provisional. `36.32%` of frames had at least one detection near a zone boundary using the current uncertainty threshold, so final zone calibration is still required.

## Safety Result

- MQTT enabled during this validation run: `false`
- Vision-only MQTT topics published during this validation run: `0`
- Relay `/set` commands published during this validation run: `0`
- Auto mode enabled: `false`

## Result

The live people-count model validation passed for Monitor-mode software testing. It does not make the system physically production-ready. Remaining blockers are final zone calibration, controlled scene validation, supervised relay/ESP32/Node-RED/Home Assistant validation, supervised Auto-mode testing, and failure testing.

## Deployed Node-RED Validation

Follow-up validation against the currently deployed `labos` Node-RED runtime was completed after the AI PC publisher was retargeted to `lab/vision/...`.

- Node-RED process on `labos`: running
- MQTT broker on `labos:1883`: reachable
- Current automation mode observed on MQTT: `manual`
- Live AI publisher source: `rtsp://hari:8554/labcam`

Observed live AI payload sample:

```json
{
  "publisher": "labvision-ai-pc",
  "timestamp": 1781611109533,
  "total_count": 0,
  "stable_count": 0,
  "zone_counts": [0, 0, 0, 0, 0, 0],
  "source_healthy": true,
  "status": "online",
  "fps": 21.277,
  "inference_ms": 10.726
}
```

Observed Node-RED processing evidence after the live publisher started:

- `lab/automation/vision_health = healthy`
- `lab/automation/vision_age_seconds = 0`
- repeated `lab/automation/accepted_count` messages with `count: 0` and `target: EMPTY`

Manual-mode safety result:

- Relay `/set` messages observed during the live run: `0`
- Relay state topics remained visible as feedback only
- Auto mode enabled in this validation step: `false`

This confirms the existing deployed `labos` Node-RED flow is receiving and processing the new AI PC `lab/vision/people_count` messages while remaining safe in Manual mode.
