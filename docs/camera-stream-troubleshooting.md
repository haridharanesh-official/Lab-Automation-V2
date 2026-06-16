# Camera Stream Troubleshooting

Date: June 16, 2026

## Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

## Verified Device Identity

- Camera bridge Pi hostname: `hari`
- LAN address: `172.16.3.31/20`
- Tailscale address: `100.66.172.14`
- Active network: wired `eth0`
- Wi-Fi: disconnected

## MediaMTX Status

MediaMTX is running on `hari` and listening on RTSP port `8554`.

Configured path:

```yaml
paths:
  labcam:
    source: publisher
```

Bridge service:

```text
labos-camera-bridge.service
```

The bridge uses ffmpeg to pull the upstream camera and publish it to:

```text
rtsp://127.0.0.1:8554/labcam
```

## Root Cause

`rtsp://hari:8554/labcam` returns `404 Not Found` because MediaMTX has no active publisher on path `labcam`.

The ffmpeg bridge cannot publish because `hari` cannot reach the upstream physical camera at:

```text
192.168.5.110:8554
```

Read-only checks from `hari`:

- `ping 192.168.5.110`: 100% packet loss
- `nc -vz 192.168.5.110 8554`: timeout
- `nc -vz 192.168.5.110 554`: timeout
- `nc -vz 192.168.5.110 80`: timeout
- `ffprobe` against the configured RTSP source: no stream

Read-only checks from the AI PC also failed to reach `192.168.5.110`.

## Required Network Fix

Do not change MediaMTX until upstream camera reachability is restored.

One of these must be corrected by the lab/network owner:

- Put `hari` on the LAN/VLAN that can route to `192.168.5.110`.
- Restore routing from `172.16.3.31/20` via gateway `172.16.3.1` to the `192.168.5.0/24` camera network.
- Confirm whether the CP Plus camera IP changed and provide the current RTSP URL.
- Confirm that the camera is powered, network-connected, and serving RTSP on the expected port.

## Current RTSP Result

```text
rtsp://hari:8554/labcam -> working after camera bridge restart
```

Five-minute AI PC decode on June 16, 2026 passed after restarting only the camera bridge service.

## Fresh Validation: June 16, 2026

Scope: camera/RTSP/MediaMTX only. No MQTT relay topics, Node-RED flows, ESP32, Home Assistant controls, Auto mode, camera reboot, or camera reconfiguration were touched.

Read-only checks from `hari`:

- Active IPs: `eth0` is `172.16.3.31/20`; `tailscale0` is `100.66.172.14/32`; `wlan0` is down.
- Routes: default route via `172.16.3.1`; direct route only for `172.16.0.0/20`.
- `ping 192.168.5.110`: 100% packet loss.
- `nc -vz 192.168.5.110 554`: timeout.
- `nc -vz 192.168.5.110 8554`: timeout.
- `ffprobe` against the configured upstream RTSP URL: no stream metadata returned.
- ffmpeg bridge socket: stuck in `SYN-SENT` from `172.16.3.31` to `192.168.5.110:8554`.

MediaMTX state:

- `mediamtx.service`: active and listening on `:8554`, `:8888`, and `:8889`.
- `labos-camera-bridge.service`: active but not publishing because upstream connection cannot complete.
- `paths.labcam.source`: `publisher`.
- Local `ffprobe rtsp://127.0.0.1:8554/labcam`: `404 Not Found`.

AI PC checks:

- `rtsp://hari:8554/labcam`: did not open; `404 Not Found`.
- 60-second decode: skipped because the stream did not open.
- Codec, resolution, FPS, dropped frames, and latency: unavailable until the stream opens.

Exact failing hop: network route/reachability from `hari` and the AI PC to upstream camera `192.168.5.110`, not the MediaMTX path definition.

## Camera Retry Validation: June 16, 2026

Scope: camera/RTSP/MediaMTX/AI Monitor validation only. Auto mode, relays, ESP32 firmware, Home Assistant controls, and physical devices were not touched. No relay `/set` commands were published.

Updated reachability from `hari`:

- `ping 192.168.5.110`: passed, 4/4 replies, 0% packet loss, about 9.5 ms average.
- `nc -vz 192.168.5.110 554`: connection refused.
- `nc -vz 192.168.5.110 8554`: succeeded.
- `nc -vz 192.168.5.110 80`: succeeded.

MediaMTX and bridge state:

- MediaMTX was active as user service `mediamtx.service`, listening on `:8554`.
- `paths.labcam.source` remained `publisher`.
- `labos-camera-bridge.service` was active but stale: upstream read had ended and the local RTSP publish socket was broken, so `/labcam` still returned `404 Not Found`.
- Safe fix applied: restarted only `labos-camera-bridge.service`. No MediaMTX config change and no camera reconfiguration were performed.

Restored stream:

- Local on `hari`: `rtsp://127.0.0.1:8554/labcam` opened.
- AI PC URL: `rtsp://hari:8554/labcam`.
- Codec: HEVC/H.265.
- Resolution: `1280x720`.
- FPS: `25`.
- Five-minute AI PC decode: passed. FFmpeg reported initial HEVC reference-frame warnings, then stayed connected and exited cleanly after 300 seconds.

Monitor-safe AI validation:

- Tool: `tools/live_monitor_validation.py`.
- Model: `models/backcam_yolov8s_improved_v3_hardfp.pt`.
- Confidence: `0.35`.
- Image size: `1280`.
- Device: CUDA `0`, `NVIDIA GeForce RTX 5070`.
- Tracker: `bytetrack.yaml`.
- Duration: `300.016` seconds.
- Frames processed: `7,484`.
- Processing FPS: `24.95`.
- Average inference latency: `15.23 ms`.
- P95 inference latency: `20.75 ms`.
- Decode failures: `0`.
- Reconnect events: `0`.
- Partial windows cleared: `0`.
- False-zero reports: `0`.
- MQTT imported: `false`.
- Reports published: `0`.
- Relay `/set` commands: `0`.

Remaining camera note: the bridge service should be monitored for stale ffmpeg sessions after upstream interruptions. A future hardening pass should make the bridge exit and restart cleanly on broken local publish sockets.
