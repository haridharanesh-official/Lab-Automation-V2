# Production Readiness Report

Date: June 16, 2026

## Final Readiness Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

Lab Automation v2.0 must not be described as physically production-ready until live camera, MQTT, ESP32 relay, Node-RED, Home Assistant, zone calibration, supervised Auto mode, and failure tests all pass on real hardware.

## Software Readiness

Status: Software validation complete

- Local tests: 18 passed
- Dependencies: no broken requirements
- AI publisher safety: refuses relay/control/set/command topics
- Live deployment contract update: AI telemetry now targets `lab/vision/...` topics consumed by the current `labos` Node-RED runtime.
- Monitor-mode software tests: zero relay commands
- Relay mapping logic and fan OR rules: validated in tests
- Two-empty-report shutdown: validated in tests
- Camera-failure window clearing: validated in tests
- GPIO 5 excluded from firmware
- Relay 1 mapped to GPIO 33 in firmware

## Camera Readiness

Status: Camera stream restored; hardware deployment pending

- RTSP service port on `hari:8554`: reachable
- Stream URL tested: `rtsp://hari:8554/labcam`
- Result: working after restarting only `labos-camera-bridge.service`
- Five-minute continuous decoding: passed on AI PC
- Resolution: `1280x720`
- Codec: HEVC/H.265
- FPS: `25`
- Reconnect behavior during validation: no reconnects observed

Root cause found on camera Pi: the college/network fix restored reachability from `hari` to upstream camera `192.168.5.110:8554`, but the ffmpeg bridge remained stale after its earlier upstream failure. MediaMTX was healthy and `paths.labcam.source` was still `publisher`; restarting only `labos-camera-bridge.service` restored `/labcam`.

Detailed troubleshooting is recorded in `docs/camera-stream-troubleshooting.md`.

Fresh June 16 retry validation:

- `hari` to `192.168.5.110`: ping passed, port `8554` open, port `80` open, port `554` refused.
- AI PC `ffprobe rtsp://hari:8554/labcam`: passed.
- AI PC five-minute decode: passed with initial HEVC reference-frame warnings only.
- Monitor-safe AI validation: 7,484 frames over 300.016 seconds, 24.95 FPS, zero decode failures, zero reconnects, zero false-zero reports.

Camera bridge hardening:

- `mediamtx.service` and `labos-camera-bridge.service` are enabled for the `hari` user and start on boot.
- Camera credentials were moved into `~/.config/labos-camera-bridge.env` on `hari`, outside repo-tracked files.
- Added `labcam-healthcheck.service` and `labcam-healthcheck.timer` on `hari` to probe `rtsp://127.0.0.1:8554/labcam` and restart only the bridge if the path returns `404`.
- Bridge service restart behavior now includes a 15-second delay and systemd start-rate limiting.
- Verification after bridge restart: passed.
- Verification after MediaMTX restart: passed.
- Local five-minute decode on `hari`: passed.
- AI PC `ffprobe` and 30-second decode of `rtsp://hari:8554/labcam`: passed.
- Remaining stream issue: occasional HEVC reference-frame warnings still appear during decode.

Ten-minute live model validation:

- Model/settings: `backcam_yolov8s_improved_v3_hardfp.pt`, confidence `0.35`, image size `1280`, CUDA `0`, ByteTrack, people class only.
- Runtime: 600.0 seconds; frames processed: 9,832; average FPS: 16.39.
- Average inference latency: 13.70 ms; p95 latency: 18.04 ms; peak GPU memory: 188.83 MB.
- Detection coverage: people in 9,753 frames; 2+ people in 9,701 frames; max people detected: 7.
- Duplicate-box frames: 9, duplicate rate: 0.0915%.
- False-zero events: 7.
- Decode failures: 1; reconnect attempts/events: 40.
- Result: live vision ran for the requested duration, but intermittent RTSP `404` periods and camera bridge restarts remain a camera stability blocker.

Ten-minute live people-count validation:

- Runtime: 600.015 seconds; frames processed: 14,984; average FPS: 24.97.
- Average inference latency: 13.76 ms; p95 latency: 17.95 ms; peak GPU memory: 188.83 MB.
- Detection coverage: people in 14,968 frames; 2+ people in 14,668 frames; max people detected: 6.
- Duplicate-box frames: 53, duplicate rate: 0.354%.
- False-zero events: 0.
- Decode failures: 0; reconnects: 0.
- Result: live overlay and per-frame logging passed for Monitor-mode validation.

## MQTT Readiness

Status: Partially verified

- Broker `labos:1883`: reachable
- Safe Monitor-mode publish path updated to `lab/vision/...`
- Short live AI publish verification to `lab/vision/...`: passed
- Exact topics observed from AI: `lab/vision/people_count`, `lab/vision/status`, `lab/vision/source_status`, `lab/vision/heartbeat`
- Observed `lab/control/+/set` publishes from AI during verification: 0
- Relay `/set` commands observed during Monitor test: 0
- AI publishes outside approved vision topics: not observed in tests
- Camera retry Monitor validation used MQTT disabled; reports published: 0; relay `/set` commands: 0
- Ten-minute live model validation used MQTT disabled; reports published: 0; relay `/set` commands: 0
- Ten-minute live people-count validation used MQTT disabled; reports published: 0; relay `/set` commands: 0

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

- Importable repo v2 flow exists, but deployed `labos` runtime currently consumes `lab/...` AI topics instead of the earlier repo draft `labos/v2/...` topic plan.
- Deployed Node-RED process on `labos`: running
- Deployed runtime mode observed on MQTT during validation: `manual`
- Live AI -> MQTT -> deployed Node-RED path: verified
- Node-RED processed live AI counts and published `lab/automation/accepted_count`, `lab/automation/vision_health`, and `lab/automation/vision_age_seconds`
- Live broker Manual-mode test produced zero relay `/set` commands.
- No `labos/v2/automation/decision` response was observed after a simulated report, indicating the v2 flow/controller is not currently verified as deployed and active.

## Home Assistant Readiness

Status: Hardware deployment pending

- MQTT configuration exists for mode/status entities.
- Ten relay switches, six zone sensors, warning/status/mismatch entities still require live Home Assistant verification.

## Zone Calibration Readiness

Status: Hardware deployment pending

- Existing `config/zones.json` now uses rough slanted perspective polygons from the user-marked back-camera reference.
- Zone numbering matches the reference: bottom row right-to-left is Zones 1, 2, 3; top row right-to-left is Zones 4, 5, 6.
- Zone 1/Zone 2 split was corrected so Zone 1 remains the bottom-right wedge and Zone 2 owns the bottom-middle table area.
- The bottom-right empty area was filled into Zone 1 with a clean shared Zone 1/Zone 2 boundary.
- Approximate zone centers and sample foot-points map uniquely in software.
- Shared boundary ambiguity is documented.
- Ten-minute live model validation saw 59.20% zone-boundary uncertainty with the provisional grid.
- Ten-minute live people-count validation saw 36.32% zone-boundary uncertainty with the provisional grid.
- Live validation with the corrected slanted zones still needs to be rerun after the interrupted calibration pass.
- Door, seated people, occlusion, and real boundaries are not physically verified.
- Do not update final zone configuration until supervised live validation passes.

## Physical Auto-Mode Readiness

Status: Not physically production-ready until supervised relay validation passes

- A short supervised Auto-mode entry/exit safety check was completed against the deployed `labos` flow.
- Auto mode entered successfully and was returned to Manual successfully.
- During that short run, live AI samples remained at zero count, so Node-RED emitted zero relay `/set` commands.
- Physical Zone 1-6 occupied tests were not run successfully in that pass because no occupied scenes were captured.
- Multiple-zone occupied tests were not run successfully in that pass.
- Real relay/light/fan switching behavior, repeated-command behavior, and flicker behavior remain unverified on hardware.

## Failure-Test Readiness

Status: Hardware deployment pending

- Camera failure behavior is validated in software.
- Live camera-stop, AI-stop, MQTT-disconnect, and ESP32-restart tests are not complete.
- Relay state preservation under real hardware failure remains pending.

## Remaining Blockers

- Keep monitoring the hardened `/labcam` bridge and health-check timer during longer unattended runs.
- Reduce or eliminate upstream HEVC reference-frame decode warnings if they affect downstream analytics.
- Deploy/import and verify the v2 Node-RED flow.
- Verify ESP32 firmware on real hardware.
- Verify Home Assistant entities.
- Complete supervised manual relay mapping.
- Complete live zone calibration.
- Complete supervised Auto-mode and failure tests.
