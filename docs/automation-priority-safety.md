# Automation Priority Safety

Date: June 16, 2026

## Priority Order

The current repo flow for the `labos` runtime is designed around this strict order:

1. Manual override
2. Timetable fallback
3. Healthy people-count automation

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

## Manual Override

Manual override has the highest priority.

- If a relay state changes while the system is in `manual`, that state is captured as a manual override.
- If relay feedback changes unexpectedly away from the last automation command, the flow treats it as a manual override as well.
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

## People-Count Automation

People-count automation is used only when vision is healthy.

Healthy means:

- service status is online/healthy
- source status is healthy
- heartbeat is fresh
- `lab/vision/people_count` is fresh

The current stage mapping remains:

- `0` => `EMPTY`
- `1` => `ONE`
- `2-3` => `TWO_THREE`
- `4+` => `FOUR_PLUS`

Relay mapping for the deployed `labos` runtime:

- `ONE` => relays `2, 7`
- `TWO_THREE` => relays `2, 3, 6, 7`
- `FOUR_PLUS` => relays `2, 3, 4, 6, 7, 8`

## No-Flicker and Safety Rules

- duplicate or stale counts are ignored
- healthy zero count uses shutdown delay, not immediate OFF
- relay commands are deduplicated against both feedback state and last command
- manual mode never emits relay `/set`
- monitor mode publishes diagnostics and intended state only
- final recovery order remains Manual, then Monitor, then supervised Auto

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
