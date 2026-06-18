# Automation Priority Safety

Date: June 16, 2026

## Priority Order

The current repo flow for the `labos` runtime is designed around this strict order:

1. Manual override
2. Timetable fallback
3. Healthy people-count automation

`mode_state` is separate from the decision source:

- `manual`, `monitor`, `auto` describe the user-selected operating mode
- `priority_state` describes why the controller is making, or not making, decisions

Node-RED alone may publish relay commands. The AI PC publishes only `lab/vision/...` telemetry and is blocked from control, relay, `/set`, and `/command` topics.

## MQTT Topics Used

### Vision input

- `lab/vision/people_count`
- `lab/vision/status`
- `lab/vision/source_status`
- `lab/vision/heartbeat`

### Automation state and diagnostics

- `lab/automation/mode`
- `lab/automation/mode_state`
- `lab/automation/status`
- `lab/automation/count_source`
- `lab/automation/manual_override/clear`
- `lab/automation/manual_override_state`
- `lab/automation/accepted_count`
- `lab/automation/intended_state`
- `lab/automation/priority_state`
- `lab/automation/vision_health`
- `lab/automation/vision_age_seconds`
- `lab/automation/last_action`
- `lab/automation/warning`

### Relay control and feedback

- `lab/control/relayX/set`
- `lab/control/relayX/state`
- `lab/control/status`

## Correct Mode Command

The live `labos` flow expects the mode command as a plain MQTT string payload on:

- topic: `lab/automation/mode`
- payload: `manual`, `monitor`, or `auto`

Recommended command examples:

```powershell
mosquitto_pub -h labos -t lab/automation/mode -r -m manual
mosquitto_pub -h labos -t lab/automation/mode -r -m monitor
mosquitto_pub -h labos -t lab/automation/mode -r -m auto
```

Notes:

- payload is not JSON
- casing is normalized to lowercase by the flow
- `mode_state` is published as a retained diagnostic message and may also be republished on later ticks
- when validating transitions, ignore stale retained history and capture fresh events after subscribing

Home Assistant note:

- The Home Assistant selector should publish to `lab/automation/mode`.
- The selector should read confirmed state from `lab/automation/mode_state`, not from the command topic.
- The selector options must include all three modes: `manual`, `monitor`, and `auto`.
- A June 17, 2026 live audit found the deployed discovery entity on `labos` still advertised only `auto` and `manual`, which is why Home Assistant rejected `monitor` selections.

## Mode And Stale Vision Behavior

The flow now keeps the selected mode and the decision source separate:

- If the user selects `auto`, `lab/automation/mode_state` stays `auto`
- stale or unhealthy vision does **not** force `mode_state` back to `manual`
- stale or unhealthy vision changes only the decision source reported by `lab/automation/priority_state`

Current `priority_state` meanings:

- `MANUAL`
- `MANUAL_OVERRIDE`
- `MONITOR`
- `PEOPLE_COUNT`
- `TIMETABLE_FALLBACK`
- `TIMETABLE_HOLD`
- `VISION_STALE`

## Manual Override

Manual override has the highest priority.

- If a relay state changes while the system is in `manual`, that state is captured as a manual override.
- Relay feedback changes in `auto` are not captured as manual overrides. Auto-mode feedback mismatch is treated as something the automation should correct.
- Active manual overrides are published under `lab/automation/manual_override_state`.
- Automation overlays those manual states onto any fallback or people-count target.

### Clearing manual override

Manual override is cleared explicitly using:

- topic: `lab/automation/manual_override/clear`

Payload options:

- `all`
- a single relay number such as `2`
- an array of relay numbers such as `[2,7]`

## Timetable Fallback

If vision is unhealthy, stale, frozen, or unavailable, the flow does not trust people count.

Fallback windows:

- `08:30` to `12:30`
- `13:00` to `16:30`

Behavior during fallback windows:

- preserve last known automation state if one exists
- otherwise use the configured fallback ON state:
  - relays `2, 3, 4, 6, 7, 8` ON

Behavior outside fallback windows:

- do not turn everything OFF immediately
- preserve the last known automation state first
- allow OFF only after the configured safe delay

When mode is `auto` and vision becomes stale or unhealthy:

- `mode_state` remains `auto`
- `priority_state` moves to `VISION_STALE`
- people count is ignored until vision is healthy again
- Node-RED preserves current/last-known relay state and emits zero relay `/set` commands

## People-Count Automation

People-count automation is used only when vision is healthy. This is the active Auto behavior for now: Node-RED uses the total debounced count from `lab/vision/people_count.stable_count`, not per-zone counts. The retained diagnostic topic `lab/automation/count_source` should publish `total-count`.

Healthy means:

- service status is online/healthy
- source status is healthy
- heartbeat is fresh
- `lab/vision/people_count` is fresh

Zone mapping remains provisional and is used for display/debug validation only. `zone_counts` may be present in the payload, and `zone-count` publisher mode can produce zone counts for future validation, but it must not drive Auto relay decisions until zone calibration is physically validated and Node-RED is explicitly switched to a zone-count source.

The current 8-relay stage mapping is:

- `0` => `ZERO_HOLD`, then `EMPTY_STAGE` after 60 continuous seconds
- `1-3` with high-load latch inactive => `LOW_STAGE`
- `1-3` with high-load latch active => `HIGH_STAGE`
- `4+` => `HIGH_STAGE` and high-load latch active

Relay mapping for the deployed `labos` runtime:

- `EMPTY_STAGE` => relays `2, 3, 4, 6, 7, 8` OFF only after the 60-second empty delay
- `LOW_STAGE` => both lights + Fan 1 + Fan 4 ON: relays `2, 3, 6, 7`; relays `4, 8` OFF
- `HIGH_STAGE` => both lights + all fans ON: relays `2, 3, 4, 6, 7, 8`

Relays `1` and `5` are spare on the current live 8-channel hardware and must never be commanded by automation. Ten-relay support is future planned only.

The high-load latch exists to prevent relay flicker when the count jumps between `3` and `4` or people move through camera blind spots. Once `HIGH_STAGE` is reached, the system remains in `HIGH_STAGE` until `stable_count = 0` is healthy and continuous for 60 seconds.

## No-Flicker and Safety Rules

- duplicate or stale counts are ignored
- healthy zero count uses shutdown delay, not immediate OFF
- relay commands are deduplicated against feedback state and the last observed correction condition
- manual mode never emits relay `/set`
- monitor mode publishes diagnostics and intended state only
- final recovery order remains Manual, then Monitor, then supervised Auto

## Relay Controller Power Recovery

Node-RED subscribes to `lab/control/status` from the ESP32 relay node.

If the relay node reports `offline`, Node-RED clears its confirmed relay feedback cache and its last-command cache. This handles lab power-loss cases where the ESP32/relay board loses power and physical loads turn OFF while the AI PC, camera, and people count stay online.

Relay state feedback in Auto is not treated as a manual override. If feedback differs from the desired Auto state, Node-RED should correct it rather than freezing the wrong state. Manual overrides are captured only in Manual mode, where the operator is intentionally controlling relays.

When the relay node reports `online` again:

- Manual mode still sends no automation relay commands.
- Monitor mode still sends no physical relay commands.
- Auto mode recomputes desired state from the latest healthy `lab/vision/people_count.stable_count`.
- If vision is healthy, Node-RED recomputes desired state from `stable_count`, current stage, and the high-load latch.
- If `stable_count = 0`, the 60-second empty timer is honored before OFF commands are allowed.
- Node-RED sends one reconciliation command for each controlled relay whose feedback is unknown or different.
- Relay `/set` commands remain non-retained.
- Repeated `online` status messages do not spam duplicate relay commands.

This fixes the case where `stable_count` does not change, but the relay outputs must still be restored after ESP32/relay power returns.

## Periodic Feedback Reconciliation

Node-RED also performs a safe Auto-only relay feedback reconciliation on the controller tick, currently every 10 seconds.

During this reconciliation:

- Manual mode emits zero automation relay commands.
- Monitor mode emits zero physical relay commands.
- Auto mode runs only when vision is healthy and a latest `stable_count` exists.
- Node-RED recomputes the desired people-count stage from the latest `stable_count`.
- If desired relay state differs from `lab/control/relayX/state`, Node-RED sends one non-retained correction command.
- If feedback already matches the desired state, Node-RED sends no relay command.

This covers the second power-loss shape: the ESP32 may come back online without a clean new `offline -> online` transition being observed by Node-RED, or a relay may report `OFF` after the desired Auto state was already remembered as `ON`. The periodic check corrects that mismatch without waiting for `stable_count` to change and without blindly publishing repeated ON commands.

## Live Deployment Validation on `labos`

Date: June 16, 2026

- Deployed repo flow to live `labos` Node-RED via the admin API.
- Backed up the previous live flow to `/home/labos/labos-v2-backups/nodered/flows-20260616-213250.json`.
- Verified the deployed flow contains `Priority Safety Controller`, `manual_override/clear`, and `TIMETABLE_FALLBACK`.
- Verified retained mode returned to `manual` immediately after deployment.
- Observed zero relay `/set` messages during deployment/startup validation.

Simulation-only live checks completed with final mode kept in `manual`:

- healthy people-count path:
  - `lab/automation/intended_state` published a valid `TWO_THREE` target in Monitor mode
  - relay `/set` commands observed: `0`
- `source_healthy=false` / invalid people-count payload:
  - `lab/automation/warning` published `invalid people_count payload ignored`
  - `lab/automation/priority_state` moved to `TIMETABLE_HOLD`
- stale heartbeat / stale vision:
  - after heartbeat expiry, `lab/automation/priority_state` remained on fallback
  - `lab/automation/vision_health` published `stale`
- manual override:
  - relay state feedback in Manual mode produced `lab/automation/manual_override_state {"2":"OFF"}`
  - clearing `lab/automation/manual_override/clear` returned `lab/automation/manual_override_state {}`

Notes:

- Live validation was performed outside the timetable windows, so `TIMETABLE_HOLD` was the expected fallback stage.
- The inside-window fallback branch (`TIMETABLE_FALLBACK`) remains covered by software tests and still needs a live time-window validation pass during `08:30-12:30` or `13:00-16:30`.
- No Auto-mode relay validation was performed in this deployment step.

## Relay Reconnect Validation on `labos`

Date: June 18, 2026

- Deployed the relay reconnect reconciliation fix to live Node-RED.
- Backed up the previous live flow to `/home/labos/labos-v2-backups/nodered/flows-20260618-before-relay-resync.json`.
- Controlled MQTT validation simulated relay node power loss/recovery:
  - `lab/control/status offline` cleared known relay feedback and last-command state.
  - `lab/control/status online` in Auto mode with fresh healthy `stable_count = 7` recomputed `FOUR_PLUS`.
  - Node-RED published one non-retained ON command each for relays `2,3,4,6,7,8`.
  - State feedback returned for relays `2,3,4,6,7,8`.
  - A repeated `online` status produced `0` relay `/set` messages.
- Final live snapshot after the test showed `mode_state = auto`, `lab/control/status = online`, and `lab/automation/relay_status = online`.
- The warning later showed stale/fallback when no fresh current people-count message was observed in the short snapshot; that is expected if the live AI publisher is not currently refreshing `lab/vision/people_count`.
- Follow-up live correction found the blocking state was `lab/automation/manual_override_state {"2":"OFF","3":"OFF","4":"OFF","6":"OFF","7":"OFF","8":"OFF"}` while Auto and people count were healthy. Clearing manual overrides and reconciling relay status restored `FOUR_PLUS` relays `2,3,4,6,7,8` to ON.
- The Node-RED flow was then updated so Auto-mode relay feedback mismatches no longer create manual overrides. After redeploy, live Auto showed `manual_override_state {}`, `priority_state PEOPLE_COUNT`, `stage = FOUR_PLUS`, and all controlled relay states ON.
- A follow-up deploy added periodic Auto feedback reconciliation. Controlled MQTT validation forced `lab/control/relay2/state OFF` while the desired `FOUR_PLUS` state required relay 2 ON; the next tick sent exactly one `lab/control/relay2/set ON`, feedback returned ON, and subsequent ticks did not spam more relay commands.
