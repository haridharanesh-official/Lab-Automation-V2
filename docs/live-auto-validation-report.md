# Live Auto-Mode Validation

Date: June 16, 2026

## Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

## Scope

This run used the deployed `labos` Node-RED automation together with the AI PC live publisher on `lab/vision/...`.

- Camera stream: `rtsp://hari:8554/labcam`
- MQTT broker: `labos:1883`
- AI publisher topics:
  - `lab/vision/people_count`
  - `lab/vision/status`
  - `lab/vision/source_status`
  - `lab/vision/heartbeat`
- Auto mode was enabled only for a short supervised observation window and then returned to Manual.

## Supervision

Physical supervision was confirmed by the user before the run.

## Mode Transitions

Observed on MQTT:

- `lab/automation/mode = manual`
- `lab/automation/mode_state = manual`
- `lab/automation/mode = auto`
- `lab/automation/mode_state = auto`
- `lab/automation/mode = manual`
- `lab/automation/mode_state = manual`

Final mode after the run: `manual`

## People-Count Samples

Observed live AI payload sample during the supervised window:

```json
{
  "publisher": "labvision-ai-pc",
  "timestamp": 1781611754063,
  "total_count": 0,
  "stable_count": 0,
  "zone_counts": [0, 0, 0, 0, 0, 0],
  "source_healthy": true,
  "status": "online",
  "fps": 21.277,
  "inference_ms": 11.665
}
```

The short supervised run observed only zero-count samples. Because no occupied scenes were captured during the Auto observation window, the staged occupancy cases (one person, two to three people, four or more people) were not validated in this pass.

## Node-RED Processing

The deployed `labos` flow processed the live AI telemetry:

- `lab/automation/accepted_count` was published repeatedly with `count: 0` and `target: EMPTY`
- `lab/automation/vision_health` changed to `healthy`
- `lab/automation/vision_age_seconds` updated to `0`
- `lab/automation/zero_shutdown_remaining_seconds` counted down during Auto mode

This confirms the Auto path was active and consuming live AI data.

## Relay Commands And State Feedback

- Relay `/set` commands observed during Manual mode: `0`
- Relay `/set` commands observed during the supervised Auto window: `0`
- Relay state feedback remained visible on `lab/control/+/state`
- All observed relay states during this pass remained `OFF`

Because all observed AI counts were zero, Auto mode never had a valid occupied-stage trigger to issue relay commands. As a result, this run does **not** verify real ON/OFF relay behavior, light/fan mapping, or repeated-command/flicker behavior under occupied scenes.

## Camera/Failure Safety Observations

- `lab/automation/vision_health` was initially `stale`, then became `healthy` after live AI resumed
- No unsafe relay `/set` behavior occurred during the transition
- No camera-stop failure test was executed in this pass

## Result

This supervised run verified:

- live AI publisher to deployed Node-RED Auto path works
- Auto mode can be entered and exited safely
- final mode returned to Manual
- zero-count Auto handling did not emit unsafe relay commands

This supervised run did **not** complete final hardware validation because the required staged occupied-scene cases were not observed. Physical production readiness remains blocked on:

- one-person occupied test
- two-to-three-person occupied test
- four-or-more-person occupied test if supported by the room
- real relay/light/fan mapping confirmation
- repeated-command and flicker observation under real load changes
- camera interruption behavior under supervised Auto mode
