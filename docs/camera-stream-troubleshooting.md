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
rtsp://hari:8554/labcam -> 404 Not Found
```

Five-minute continuous decoding, codec, resolution, FPS, and reconnect behavior remain unverified until the upstream camera is reachable.
