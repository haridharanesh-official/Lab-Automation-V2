# LabOS Automation Logic Reference

Last verified: 2026-06-17

This document describes the current Lab Automation v2.0 runtime contract using the live `lab/...` MQTT namespace. It separates the AI PC, Node-RED automation authority, Home Assistant UI, and ESP32 relay feedback path.

## Runtime Authority

- AI PC publishes vision telemetry only under `lab/vision/#`.
- Node-RED is the automation authority. It reads mode and vision topics, computes decisions, and publishes relay `/set` commands only in Auto mode.
- Home Assistant is the UI/manual-control surface. It publishes mode commands and relay switch commands.
- ESP32 receives relay commands and publishes relay state feedback.

The AI publisher rejects any non-vision topic and rejects topics containing `/relay/`, `/control/`, `/set`, or `/command`.

## AI PC Counting Modes

Configured by `counting_mode` in `config/config.yaml` or with `.\start_lab_automation.ps1 -CountingMode ...`.

| Mode | Behavior | Automation use |
| --- | --- | --- |
| `total-count` | Runs YOLO on the full frame and counts people only. Zone polygons are not required. `zone_counts`, `raw_zone_counts`, and `window_zone_counts` publish as `null`. | Current deployed Auto source. |
| `zone-count` | Runs YOLO on the full frame and assigns each detected person to a zone using the bounding-box bottom-centre point. | Available for calibration/debug; not the current Auto source. |

Current model/camera defaults:

| Setting | Value |
| --- | --- |
| Camera stream | `rtsp://hari:8554/labcam` |
| Reconnect delay | `5` seconds |
| Model | `models/backcam_yolov8s_improved_v3_hardfp.pt` |
| Confidence | `0.35` |
| Image size | `1280` |
| Device | CUDA device `0` |
| Tracker | `bytetrack.yaml` |
| Report/window seconds | `60` |
| Heartbeat interval | `10` seconds |
| Stable/debounce publish interval | About `1` second |

## People Count Payloads

The AI publishes:

- `lab/vision/status` retained, usually `online`
- `lab/vision/source_status` retained, usually `healthy`
- `lab/vision/heartbeat` every `10` seconds
- `lab/vision/raw_people_count` non-retained, frame-level/instantaneous diagnostic count
- `lab/vision/people_count` non-retained, debounced count used by HA and Node-RED

`lab/vision/people_count` includes:

- `stable_count`: debounced count used by Node-RED
- `window_stable_count`: 60-second report-window count
- `counting_mode`: `total-count` or `zone-count`
- `zone_counts`: `null` in `total-count`; per-zone debounced counts in `zone-count`
- `source_healthy`: boolean
- `status`: `online`
- `fps` and `inference_ms`

Debounce behavior:

- A new non-zero count must remain stable for about `3` seconds before replacing the published count.
- A zero count must remain stable for about `10` seconds before replacing the published count.
- If the source is unhealthy, the last published count is preserved instead of publishing a false zero.
- The 60-second window count remains separate from the debounced automation/HA count.

## Node-RED Timing Constants

From the deployed priority controller:

| Constant | Value | Meaning |
| --- | ---: | --- |
| `STABLE_READINGS` | `3` | Count stage must repeat 3 accepted readings before applying a new stage. |
| `FRESH_MS` | `15000` ms | Vision heartbeat and people count must both be newer than 15 seconds. |
| `ZERO_OFF_MS` | `300000` ms | Empty room must persist for 5 minutes before OFF is allowed. |
| `MIN_CHANGE_MS` | `8000` ms | Minimum 8 seconds between applied automation stage changes. |
| `OUTSIDE_WINDOW_OFF_MS` | `300000` ms | Outside timetable fallback, preserve last state for 5 minutes before delayed OFF. |
| `AUTOMATION_COUNT_SOURCE` | `total-count` | Node-RED Auto currently reads total debounced `stable_count`, not zones. |

Fallback timetable windows:

- `08:30-12:30`
- `13:00-16:30`

## Mode Behavior

| Mode | Relay behavior |
| --- | --- |
| Manual | Automation does not change relays. AI may keep publishing vision telemetry. Manual/HA relay changes are preserved as manual overrides. |
| Monitor | Node-RED processes counts and publishes diagnostics/intended state only. Relay `/set` command count must remain `0`. |
| Auto | Node-RED publishes relay commands only when the desired state differs from confirmed state and the last command. Commands are not retained. |

Mode topics:

- Command: `lab/automation/mode`
- State: `lab/automation/mode_state`

## People-Count Auto Rules

Node-RED ignores `zone_counts` for current Auto. It reads `lab/vision/people_count.stable_count`.

| Stable count | Stage | Desired controlled relays |
| ---: | --- | --- |
| `0` | `EMPTY` / `ZERO_HOLD` | After continuous empty delay, all controlled loads OFF |
| `1` | `ONE` | both lights ON, all fans OFF |
| `2-3` | `TWO_THREE` | both lights + Fan 1 + Fan 4 ON |
| `4+` | `FOUR_PLUS` | both lights + all fans ON |

Controlled relay set: `2, 3, 4, 6, 7, 8`.

## Relay and Load Mapping

Verified from live Home Assistant MQTT discovery:

| Load | Command topic | State topic |
| --- | --- | --- |
| Light A4 | `lab/control/relay7/set` | `lab/control/relay7/state` |
| Light B2 | `lab/control/relay2/set` | `lab/control/relay2/state` |
| Fan 1 | `lab/control/relay3/set` | `lab/control/relay3/state` |
| Fan 2 | `lab/control/relay8/set` | `lab/control/relay8/state` |
| Fan 3 | `lab/control/relay4/set` | `lab/control/relay4/state` |
| Fan 4 | `lab/control/relay6/set` | `lab/control/relay6/state` |
| Spare relay 1 | `lab/control/relay1/set` | `lab/control/relay1/state` |
| Spare relay 5 | `lab/control/relay5/set` | `lab/control/relay5/state` |

## Warning and Stale Vision Behavior

Healthy vision publishes retained:

```text
lab/automation/warning = none
```

Stale or unhealthy vision publishes a retained warning such as:

```text
vision unhealthy -> timetable fallback
```

If vision becomes stale/unhealthy in Auto:

- `mode_state` remains `auto`.
- People count is not trusted.
- Node-RED uses timetable fallback/hold behavior.
- It does not immediately turn everything OFF because of camera/AI failure.

## No-Flicker and Dedup Behavior

Node-RED deduplicates relay commands against:

- confirmed `lab/control/relayX/state`
- last command sent by automation
- minimum stage-change interval
- stable-reading requirement
- empty-delay requirement

Relay `/set` commands are emitted only in Auto and are sent with `retain=false`.

## Live Snapshot

Direct MQTT inspection from the AI PC on 2026-06-17 showed:

| Topic | Observed value |
| --- | --- |
| `lab/automation/mode_state` | `auto` |
| `lab/automation/warning` | `none` |
| `lab/automation/priority_state` | `PEOPLE_COUNT` |
| `lab/automation/status` | `online` |
| `lab/vision/people_count` | `counting_mode = total-count`, `stable_count = 0`, `zone_counts = null`, `source_healthy = true` |
| `lab/automation/intended_state` | `stage = EMPTY`, controlled relays `2,3,4,6,7,8 = OFF`, `decision_source = PEOPLE_COUNT` |
| retained relay states observed | relays `2,3,4,6,7,8,9,10 = OFF` |

SSH shell inspection of `labos` was attempted during this documentation pass, but the SSH command timed out from the Codex session. Direct MQTT inspection against broker `labos:1883` succeeded and was used for the live snapshot above.

## Safe Verification Commands

Read current mode:

```powershell
.\.venv\Scripts\python.exe -c "import paho.mqtt.subscribe as s; print(s.simple('lab/automation/mode_state', hostname='labos').payload.decode())"
```

Read current people count:

```powershell
.\.venv\Scripts\python.exe -c "import paho.mqtt.subscribe as s; print(s.simple('lab/vision/people_count', hostname='labos').payload.decode())"
```

Start AI total-count display:

```powershell
.\start_lab_automation.ps1 -Display -CountingMode total-count
```

Start AI zone-count debug display:

```powershell
.\start_lab_automation.ps1 -Display -CountingMode zone-count
```

Monitor relay commands during Monitor mode:

```bash
mosquitto_sub -h localhost -v -F '%I %t %p' -t 'lab/control/+/set'
```
