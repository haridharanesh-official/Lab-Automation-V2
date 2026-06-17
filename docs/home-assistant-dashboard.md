# Home Assistant Dashboard

This page documents the LabOS Home Assistant dashboard setup for the live camera and automation status. It uses the live `lab/...` runtime namespace and does not change relay, Node-RED, ESP32, or AI publishing behavior.

## Live Camera Stream

Camera stream:

```text
rtsp://hari:8554/labcam
```

Verification from the AI PC on 2026-06-17:

```text
codec_name=hevc
width=1280
height=720
r_frame_rate=25/1
```

Verification from the Home Assistant host on `labos` on 2026-06-17:

```text
codec_name=hevc
width=1280
height=720
r_frame_rate=25/1
```

The exact `labos` verification command was:

```bash
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 rtsp://hari:8554/labcam
```

## Recommended Home Assistant Setup

Use the Generic Camera integration:

| Field | Value |
| --- | --- |
| Name | `LabOS Live Camera` |
| Stream URL | `rtsp://hari:8554/labcam` |
| Authentication | none |
| Transport | TCP if the UI exposes the option |

Expected entity:

```text
camera.labos_live_camera
```

Prefer adding the camera through the Home Assistant UI first:

1. Open Home Assistant.
2. Go to Settings -> Devices & services.
3. Add integration -> Generic Camera.
4. Set the stream source to `rtsp://hari:8554/labcam`.
5. Leave authentication blank.
6. Save and confirm `camera.labos_live_camera` appears.

If the UI flow is not available or does not persist correctly, use the repo snippet:

```yaml
camera: !include camera.yaml
```

with [home-assistant/camera.yaml](../home-assistant/camera.yaml).

Live deployment note: the `labos` Home Assistant container uses `/home/labos/labos-edge/docker/homeassistant` mounted as `/config`. The live deployment added:

- `/config/camera.yaml`
- `camera: !include camera.yaml` in `/config/configuration.yaml`
- a `picture-entity` card at the top of `/config/labos-dashboard.yaml`

Backups were written under:

```text
/home/labos/labos-v2-backups/homeassistant-camera/
```

Home Assistant config check passed before restart, and the `labos-homeassistant` container restarted successfully.

## Dashboard Layout

Place the camera near the top of the LabOS dashboard, close to:

- Automation mode
- People count
- Vision source/health
- Warning
- Current decision source
- Relay/load states

Use [home-assistant/dashboard-labos-camera.yaml](../home-assistant/dashboard-labos-camera.yaml) as the Lovelace card reference. The first card is:

```yaml
type: picture-entity
entity: camera.labos_live_camera
name: LabOS Live Camera
camera_view: live
show_name: true
show_state: false
```

The companion cards show the live LabOS entity names currently used in the dashboard:

- `select.labos_automation_controller_labos_automation_mode`
- `sensor.labos_automation_controller_labos_people_count`
- `sensor.labos_automation_controller_labos_automation_vision_health`
- `sensor.labos_automation_controller_labos_automation_warning`
- `sensor.labos_automation_controller_labos_automation_status`
- `sensor.labos_automation_controller_labos_last_action`
- relay switches mapped to their physical loads

## Relay Mapping Shown On Dashboard

| Dashboard label | Entity | MQTT command | MQTT state |
| --- | --- | --- | --- |
| Light A4 | `switch.labos_final_lab_relay_node_01_4_lights` | `lab/control/relay7/set` | `lab/control/relay7/state` |
| Light B2 | `switch.labos_final_lab_relay_node_02_2_lights` | `lab/control/relay2/set` | `lab/control/relay2/state` |
| Fan 1 | `switch.labos_final_lab_relay_node_03_fan_1` | `lab/control/relay3/set` | `lab/control/relay3/state` |
| Fan 2 | `switch.labos_final_lab_relay_node_04_fan_2` | `lab/control/relay8/set` | `lab/control/relay8/state` |
| Fan 3 | `switch.labos_final_lab_relay_node_05_fan_3` | `lab/control/relay4/set` | `lab/control/relay4/state` |
| Fan 4 | `switch.labos_final_lab_relay_node_06_fan_4` | `lab/control/relay6/set` | `lab/control/relay6/state` |

MQTT discovery confirmed these command/state topics before the live camera card was added.

## Live Deployment Result

- AI PC RTSP check: passed.
- `labos` RTSP check: passed.
- Home Assistant config check: passed.
- Home Assistant restart: `labos-homeassistant` restarted and came back up.
- Dashboard YAML: `camera.labos_live_camera` card inserted at the top.
- Home Assistant logs after restart: no camera, generic-camera, stream, ffmpeg, RTSP, invalid-config, or error lines were found in the checked startup window.
- Recorder database did not yet show a stored `camera.labos_live_camera` state during the immediate post-restart query. Visual browser confirmation is still required.

The change did not modify Node-RED, ESP32 firmware, relay MQTT topics, or Auto mode logic.

## Validation Checklist

After adding the camera:

1. Confirm `camera.labos_live_camera` appears in Home Assistant.
2. Open the dashboard and confirm the live feed renders.
3. Confirm the automation mode selector still reads from `lab/automation/mode_state`.
4. Confirm people count still reads from `lab/vision/people_count`.
5. Confirm warning still reads `none` when vision is healthy.
6. Confirm Node-RED and people-count Auto continue unchanged.
7. Confirm no retained relay `/set` messages were created by the dashboard change.

Safe relay-topic check:

```bash
mosquitto_sub -h localhost -v -F '%I %t %p' -t 'lab/control/+/set'
```

Adding the camera must not publish or change any `lab/control/#` topic.

## Troubleshooting

If the picture card does not render:

1. Confirm the stream with `ffprobe` from the Home Assistant host.
2. Check Home Assistant logs for `camera`, `stream`, `ffmpeg`, or RTSP errors.
3. Try the Generic Camera UI flow before editing YAML.
4. Restart only Home Assistant if YAML was changed.
5. Do not change the MediaMTX bridge on `hari` unless the RTSP stream itself fails outside Home Assistant.

Common stream details:

- Codec: HEVC / H.265
- Resolution: 1280x720
- Frame rate: 25 FPS

If the browser cannot display the stream reliably, Home Assistant may need its stream/ffmpeg pipeline checked for HEVC handling. That is a Home Assistant rendering issue, not automatically a camera bridge failure.

If HEVC/H.265 is the browser problem, keep the original `rtsp://hari:8554/labcam` stream unchanged for the AI PC and add a separate HA-friendly stream. Preferred fallback:

- create a second MediaMTX/FFmpeg path for Home Assistant only
- transcode or restream to H.264 or MJPEG
- expose it as a separate HA camera entity
- do not change the AI PC stream unless separately validated

## Suggested Next Home Assistant Features

High priority:

- Emergency Manual Safe Mode button that publishes retained `lab/automation/mode = manual`.
- Empty-room 5-minute countdown display based on Node-RED zero-hold timing.
- AI freshness / last update age card from heartbeat and people-count age.
- Relay command-vs-feedback mismatch panel.
- Current decision card showing `EMPTY`, `ONE`, `TWO_THREE`, or `FOUR_PLUS`.

Medium priority:

- No-flicker audit panel showing last stage change and repeated-command suppression.
- Last relay command log.
- LabOS health summary for AI PC, MQTT, Node-RED, ESP32, and camera.
- Smart-board read-only dashboard with camera, count, mode, warning, and current loads.

Future:

- Energy monitoring.
- Temperature/humidity based fan assist.
- Door/contact sensor.
- Timetable/schedule mode UI.
- Notifications for AI stale, ESP32 offline, relay mismatch, or camera stream failure.
