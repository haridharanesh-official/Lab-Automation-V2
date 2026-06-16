# Production Readiness Report

Date: June 16, 2026

## Final Readiness Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

Lab Automation v2.0 must not be described as physically production-ready until live camera, MQTT, ESP32 relay, Node-RED, Home Assistant, zone calibration, supervised Auto mode, and failure tests all pass on real hardware.

## Software Readiness

Status: Software validation complete

- Local tests: 11 passed
- Dependencies: no broken requirements
- AI publisher safety: refuses relay/control/set/command topics
- Monitor-mode software tests: zero relay commands
- Relay mapping logic and fan OR rules: validated in tests
- Two-empty-report shutdown: validated in tests
- Camera-failure window clearing: validated in tests
- GPIO 5 excluded from firmware
- Relay 1 mapped to GPIO 33 in firmware

## Camera Readiness

Status: Hardware deployment pending

- RTSP service port on `hari:8554`: reachable
- Stream URL tested: `rtsp://hari:8554/labcam`
- Result: failed, `404 Not Found`
- Five-minute continuous decoding: not passed
- Resolution, codec, FPS, reconnect behavior: not verified

Root cause found on camera Pi: MediaMTX is running, but `/labcam` has no active publisher because the upstream physical camera source at `192.168.5.110:8554` is unreachable from `hari`.

Detailed troubleshooting is recorded in `docs/camera-stream-troubleshooting.md`.

## MQTT Readiness

Status: Partially verified

- Broker `labos:1883`: reachable
- Safe Monitor-mode publish: succeeded
- Simulated vision report under `labos/v2/vision/#`: succeeded
- Relay `/set` commands observed during Monitor test: 0
- AI publishes outside `labos/v2/vision/#`: not observed

## ESP32 Readiness

Status: Hardware deployment pending

- Firmware source exists and statically maps ten active-LOW relays.
- GPIO 5 is unused.
- Relay 1 uses GPIO 33.
- Flashing final firmware: not verified in this phase.
- All relays OFF after restart: not verified on hardware.
- Manual relay 1-10 test: not run.
- Correct light/fan mapping: not physically verified.

## Node-RED Readiness

Status: Hardware deployment pending

- Importable v2 flow exists.
- Expected default mode is Manual.
- Live broker Monitor test produced zero relay `/set` commands.
- No `labos/v2/automation/decision` response was observed after a simulated report, indicating the v2 flow/controller is not currently verified as deployed and active.

## Home Assistant Readiness

Status: Hardware deployment pending

- MQTT configuration exists for mode/status entities.
- Ten relay switches, six zone sensors, warning/status/mismatch entities still require live Home Assistant verification.

## Zone Calibration Readiness

Status: Hardware deployment pending

- Existing `config/zones.json` is provisional.
- Approximate zone centers map uniquely in software.
- Shared boundary ambiguity is documented.
- Door, seated people, occlusion, and real boundaries are not physically verified.
- Do not update final zone configuration until supervised live validation passes.

## Physical Auto-Mode Readiness

Status: Not physically production-ready until supervised relay validation passes

- Auto mode was not enabled.
- Physical Zone 1-6 tests were not run.
- Multiple-zone tests were not run.
- Flicker and duplicate-command behavior were validated in software only, not on hardware.

## Failure-Test Readiness

Status: Hardware deployment pending

- Camera failure behavior is validated in software.
- Live camera-stop, AI-stop, MQTT-disconnect, and ESP32-restart tests are not complete.
- Relay state preservation under real hardware failure remains pending.

## Remaining Blockers

- Restore `/labcam` by fixing upstream camera reachability from `hari`.
- Deploy/import and verify the v2 Node-RED flow.
- Verify ESP32 firmware on real hardware.
- Verify Home Assistant entities.
- Complete supervised manual relay mapping.
- Complete live zone calibration.
- Complete supervised Auto-mode and failure tests.
