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

This confirms the deployed flow continued consuming live AI data.

## Relay Commands And State Feedback

- Relay `/set` commands observed during Manual mode: `0`
- Relay `/set` commands observed during the supervised Auto attempt: `0`
- Relay state feedback remained visible on `lab/control/+/state`
- All observed relay states during this pass remained `OFF`

Because the supervised Auto attempt did not produce any live relay `/set` traffic, this run does **not** verify real ON/OFF relay behavior, light/fan mapping, or repeated-command/flicker behavior under occupied scenes. The current blocker is that `lab/automation/mode` accepted `auto`, but the live runtime did not emit a confirming `lab/automation/mode_state = auto` update or any Auto relay activity during the staged count test.

## Camera/Failure Safety Observations

- `lab/automation/vision_health` was initially `stale`, then became `healthy` after live AI resumed
- No unsafe relay `/set` behavior occurred during the transition
- No camera-stop failure test was executed in this pass

## Result

This supervised run verified:

- live AI publisher to deployed Node-RED Auto path works
- Manual mode remained safe
- Monitor mode produced intended states with zero relay commands
- manual override capture and clear worked
- final mode returned to Manual
- the Auto attempt did not emit unsafe relay commands

This supervised run did **not** complete final hardware validation because the Auto transition was not proven active on the deployed runtime. Physical production readiness remains blocked on:

- fixing or explaining the live `mode -> auto` / `mode_state` mismatch on `labos`
- one-person occupied Auto test
- two-to-three-person occupied Auto test
- four-or-more-person occupied Auto test if supported by the room
- real relay/light/fan mapping confirmation
- repeated-command and flicker observation under real load changes
- camera interruption behavior under supervised Auto mode
