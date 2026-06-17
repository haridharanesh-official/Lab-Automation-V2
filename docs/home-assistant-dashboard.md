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

The requested read from `labos` is:

```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of default=noprint_wrappers=1 \
  rtsp://hari:8554/labcam
```

During this repo update, SSH commands to `labos` timed out from the Codex session, so the stream was verified from the AI PC instead. Direct RTSP playback should still be checked from the Home Assistant host after applying the dashboard change.

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

The companion cards show:

- `select.labos_automation_mode`
- `sensor.lab_people_count`
- `sensor.lab_vision_source_status`
- `sensor.lab_automation_vision_health`
- `sensor.lab_automation_warning`
- `sensor.lab_automation_priority_state`
- relay switches mapped to their physical loads

## Relay Mapping Shown On Dashboard

| Dashboard label | Entity | MQTT command | MQTT state |
| --- | --- | --- | --- |
| Light A4 | `switch.lab_relay_7` | `lab/control/relay7/set` | `lab/control/relay7/state` |
| Light B2 | `switch.lab_relay_2` | `lab/control/relay2/set` | `lab/control/relay2/state` |
| Fan 1 | `switch.lab_relay_3` | `lab/control/relay3/set` | `lab/control/relay3/state` |
| Fan 2 | `switch.lab_relay_8` | `lab/control/relay8/set` | `lab/control/relay8/state` |
| Fan 3 | `switch.lab_relay_4` | `lab/control/relay4/set` | `lab/control/relay4/state` |
| Fan 4 | `switch.lab_relay_6` | `lab/control/relay6/set` | `lab/control/relay6/state` |

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
