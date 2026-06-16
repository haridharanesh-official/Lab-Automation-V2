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

## Follow-up Debug Result

Later live debug isolated the `mode_state` confusion:

- the deployed `labos` flow **does** accept plain string `auto` on `lab/automation/mode`
- fresh `lab/automation/mode_state = auto` **does** publish when the subscriber is already armed
- the earlier failed check exited too early after reading the old retained `manual` state

Armed capture also showed that live Auto relay commands were being missed by the earlier check:

- staged `stable_count = 1` produced `lab/automation/intended_state` transitions `STABILIZING -> ONE`
- relay `/set` messages captured during the debug run:
  - `lab/control/relay3/set OFF`
  - `lab/control/relay4/set OFF`
  - `lab/control/relay6/set OFF`
  - `lab/control/relay8/set OFF`

This means the live flow was active in Auto during the debug run; the earlier zero-command result was a measurement issue, not proof that Auto was inactive. Physical occupied-scene validation still remains pending.

## Supervised Occupied-Scene Auto Attempt

Date: June 16, 2026

An additional supervised occupied-scene Auto validation was run with fresh MQTT capture armed before the mode switch.

Observed:

- fresh `lab/automation/mode_state = auto` confirmation appeared during the run
- final mode returned to `manual`
- live AI publisher remained limited to `lab/vision/#`

Captured people-count samples during the supervised window all remained:

```json
{
  "stable_count": 0,
  "total_count": 0,
  "zone_counts": [0, 0, 0, 0, 0, 0],
  "source_healthy": true,
  "status": "online"
}
```

Because the AI publisher never reported a non-zero stable count during that supervised run:

- no `lab/automation/intended_state` scene transitions were captured
- no relay `/set` commands were captured
- no relay feedback changes were captured

Result:

- Auto control path was confirmed active through fresh `mode_state = auto`
- occupied-scene validation was **not** achieved because the live camera/model path did not produce non-zero people counts during the staged test window

Remaining blocker for final physical validation:

- reproduce the occupied scenes in the actual camera field of view so the live model reports non-zero stable counts during Auto mode
