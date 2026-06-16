# Validation Checklist

Status labels:

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

## Safety Enforcements
- [x] Keep system in Manual/Monitor mode.
- [x] Do not publish relay `/set` commands during development.
- [x] Auto mode is not enabled physically.
- [x] No secrets, videos, large datasets, or weights are committed.
- [x] Original models and datasets are preserved.

## Vision and model
- [x] Keep `backcam_yolov8s_improved_v3_hardfp.pt` as production-safe model.
- [x] Validated candidate against duplicate boxes, missed people, false positives, etc.
- [x] Restore working RTSP `/labcam`.
- [x] Confirmed MediaMTX is running on `hari` and `labcam` path is configured.
- [x] Confirmed upstream camera `192.168.5.110` is unreachable from `hari`.
- [x] Confirmed `/labcam` has no active publisher while upstream camera is unreachable.
- [x] Confirmed AI PC cannot decode `rtsp://hari:8554/labcam` while `/labcam` returns `404`.
- [x] Confirmed restored upstream reachability from `hari` to `192.168.5.110:8554`.
- [x] Restarted only stale `labos-camera-bridge.service`; no camera, relay, ESP32, Node-RED, Home Assistant, or Auto-mode changes.
- [x] Verify five-minute continuous live decoding.
- [x] Record live resolution, codec, FPS, and reconnect behavior.
- [x] Run five-minute Monitor-safe AI validation on `rtsp://hari:8554/labcam`.
- [x] Run ten-minute live people-detection validation with annotated video and per-frame CSV/JSONL artifacts.
- [x] Run ten-minute live people-count validation with visible overlay and per-frame CSV/JSONL artifacts.
- [ ] Harden camera bridge against intermittent `/labcam` `404` periods during upstream interruptions.

## Room mapping
- [x] Verified `config/zones.json`.
- [x] Six-zone polygon mapping works with bottom-centre assignment.
- [x] Mappings marked provisional until physical tests pass.
- [ ] Reduce live zone-boundary uncertainty through final supervised calibration.

## AI publisher
- [x] Verified one-minute stable reports.
- [x] Verified 10-second heartbeat.
- [x] Verified camera failure clears windows and preserves states.
- [x] Verified unsafe MQTT topics are rejected.
- [x] Camera retry Monitor validation imported no MQTT client and published zero reports or relay `/set` commands.
- [x] Ten-minute live model validation used MQTT disabled and published zero relay `/set` commands.
- [x] Ten-minute live people-count validation used MQTT disabled and published zero relay `/set` commands.

## Node-RED
- [ ] Import v2 flow on live Node-RED.
- [ ] Confirm default mode is Manual.
- [x] Monitor MQTT test observed zero relay `/set` commands.
- [ ] Verify `labos/v2/automation/decision` response on live Node-RED.
- [x] Auto deduplicates relay commands and requires two empty reports before OFF in software tests.
- [x] Validated relay mapping in software tests.

## ESP32
- [x] Ten-relay active-LOW firmware.
- [x] GPIO 5 must not be used.
- [x] Relay 1 uses GPIO 33.
- [ ] Flash final firmware.
- [ ] Confirm all relays OFF after restart.
- [ ] Test relays 1-10 manually one by one.
- [ ] Confirm each relay controls the correct light/fan.
- [x] Safe OFF startup, MQTT reconnect, watchdog, state publishing implemented in firmware.

## Home Assistant
- [ ] Verify ten relay switches.
- [ ] Verify six zone sensors.
- [ ] Verify mode selector.
- [ ] Verify health, warning, status, and mismatch sensors.

## Testing
- [x] Run all existing tests.
- [x] Static validation passed.
- [ ] Complete supervised Auto-mode validation.
- [ ] Complete live failure tests.
