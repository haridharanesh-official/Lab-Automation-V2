# Production Readiness Report

Date: June 16, 2026

## Final Readiness Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

Lab Automation v2.0 must not be described as physically production-ready until live camera, MQTT, ESP32 relay, Node-RED, Home Assistant, zone calibration, supervised Auto mode, and failure tests all pass on real hardware.

## Software Readiness

Status: Software validation complete

- Local tests: 34 passed
- Dependencies: no broken requirements
- AI publisher safety: refuses relay/control/set/command topics
- Live deployment contract update: AI telemetry now targets `lab/vision/...` topics consumed by the current `labos` Node-RED runtime.
- Monitor-mode software tests: zero relay commands
- Relay mapping logic and fan OR rules: validated in tests
- Two-empty-report shutdown: validated in tests
- Camera-failure window clearing: validated in tests
- Live count-path update: display/counting now uses shared bottom-centre zone assignment, exposes current counts separately from rolling stable counts, and publishes debounced `lab/vision/people_count` for HA/Node-RED.
- Raw count diagnostics: `lab/vision/raw_people_count` is available for troubleshooting but is not the primary HA/automation count topic.
- Anti-flicker behavior: brief missed detections and camera/AI uncertainty do not immediately publish false zero.
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
- Updated AI topic contract: `lab/vision/people_count` is debounced/stable for HA and Node-RED, while `lab/vision/raw_people_count` carries faster diagnostic raw detections.
- Observed `lab/control/+/set` publishes from AI during verification: 0
- Relay `/set` commands observed during Monitor test: 0
- AI publishes outside approved vision topics: not observed in tests
- Camera retry Monitor validation used MQTT disabled; reports published: 0; relay `/set` commands: 0
- Ten-minute live model validation used MQTT disabled; reports published: 0; relay `/set` commands: 0
- Ten-minute live people-count validation used MQTT disabled; reports published: 0; relay `/set` commands: 0
- Empty-lab stability validation with live MQTT enabled ran for about 11 minutes in Monitor mode, kept repeated `stable_count = 0`, produced zero false positives, and emitted zero relay `/set` commands.
- June 17, 2026 startup/shutdown validation reconfirmed that both headless and display launch modes publish only `lab/vision/#` and emitted zero observed `lab/control/+/set` traffic from the AI publisher.
- June 17, 2026 live broker captures also reconfirmed fresh `lab/vision/status`, `lab/vision/source_status`, and `lab/vision/people_count` traffic while the AI publisher was running in both headless and display mode.
- June 17, 2026 flicker investigation found no active competing publisher on `labos` for `lab/vision/people_count`. Active `labos-automation.service` and `labos-system-health.service` subscribe/observe the topic and do not publish competing counts.
- The same live check found duplicate AI PC publisher processes after stopping only the PowerShell wrapper left child Python publishers alive. The Windows start/stop/status scripts were hardened to detect and stop matching orphaned `src.main --config config/config.yaml` processes.

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

- Updated repo priority-safety flow was deployed to live `labos` Node-RED on June 16, 2026.
- Live pre-deploy backup saved to `/home/labos/labos-v2-backups/nodered/flows-20260616-213250.json`.
- Repo flow design now implements priority order: manual override, then timetable fallback, then healthy people-count automation.
- Repo flow now includes documented manual override clearing and fallback windows `08:30-12:30` and `13:00-16:30`.
- Deployed Node-RED process on `labos`: running
- Deployed runtime mode observed on MQTT during validation: `manual`
- Live AI -> MQTT -> deployed Node-RED path: verified
- Node-RED processed live AI/simulated counts and published `lab/automation/mode_state`, `lab/automation/manual_override_state`, `lab/automation/priority_state`, `lab/automation/vision_health`, `lab/automation/warning`, and `lab/automation/intended_state`.
- Live broker deployment/startup relay `/set` commands observed: `0`
- Live broker simulation relay `/set` commands observed in Manual/Monitor validation: `0`
- Manual override capture and clear were verified live.
- Outside-window timetable fallback was verified live as `TIMETABLE_HOLD`.
- Healthy people-count path was verified live in Monitor mode through `intended_state` output with zero relay commands.
- Inside-window timetable fallback still needs a live validation pass during an active class window.
- Follow-up debug confirmed the correct live mode command is plain retained string payloads on `lab/automation/mode` such as `auto`; the earlier failed Auto confirmation was caused by reading the stale retained `mode_state=manual` message before the fresh `mode_state=auto` event arrived.
- A later live validation confirmed that stale or unhealthy vision does not force `mode_state` back to `manual`; `mode_state` stayed `auto` while `priority_state` moved through `VISION_STALE` and `TIMETABLE_HOLD`.
- Empty-lab stability validation later confirmed that repeated `stable_count = 0` is the correct result for the currently empty room and not evidence of a failed model.
- Follow-up end-to-end live cleanup on June 17, 2026 modernized `/home/labos/labos-edge/services/automation-bridge/automation_bridge.py` into a passive observer, so it no longer republishes `lab/automation/mode` or any relay `/set` topics.
- The live relay safety helper `/home/labos/labos-edge/services/safety-layer/relay_ack_monitor.py` was also modernized so it logs unsafe relay states and timeout errors but does not inject relay OFF commands. Node-RED is now the only relay-command publisher in the validated runtime path.
- The live system-health monitor was updated to observe the current JSON `lab/vision/people_count` topic instead of the old `/state` count topic.
- June 17, 2026 live mode-transition retest reconfirmed fresh non-retained `mode_state` updates for `manual`, `monitor`, and `auto`.
- June 17, 2026 live simulator validation reconfirmed:
  - `monitor` mode publishes intended diagnostics with zero relay `/set` commands
  - `auto` mode can drive the current mock relay path and then return to `manual`
- June 17, 2026 stale-vision retest kept `mode_state = auto`, but the live diagnostics were still noisy because `labos-mock-relay.service` and current manual-override state continued to republish healthy/people-count diagnostics during the window. That fallback path should be retested with cleaner live conditions before Auto is left enabled at the end of a validation run.
- The active helper services on `labos` are the `labos-*` units plus containerized/process-level Mosquitto, Node-RED, and Home Assistant. Generic unit names such as `mosquitto.service`, `node-red.service`, and `home-assistant.service` are not present on this host.

## Home Assistant Readiness

Status: Hardware deployment pending

- Repo Home Assistant MQTT example has been updated to the active `lab/...` runtime contract and now models `manual`, `monitor`, and `auto` against `lab/automation/mode` plus confirmed state from `lab/automation/mode_state`.
- Live Home Assistant on `labos` is reachable and serving the LabOS dashboard.
- Live dashboard currently exposes `select.labos_automation_controller_labos_automation_mode`.
- Live MQTT discovery for that selector now advertises `manual`, `monitor`, and `auto`, and points the selector state to `lab/automation/mode_state`.
- Home Assistant entity registry on June 17, 2026 confirmed the selector capabilities were updated live to `manual`, `monitor`, and `auto`.
- During live MQTT validation after the cleanup, `manual`, `monitor`, and `auto` all produced fresh matching `mode_state` updates with no forced return to `manual`.
- This June 17 run reconfirmed the live mode contract over MQTT, but did not directly drive the Home Assistant web selector UI during the session.
- Live repo/discovery configuration still matches the intended selector contract: command topic `lab/automation/mode`, state topic `lab/automation/mode_state`, options `manual`, `monitor`, `auto`.
- Ten relay switches, six zone sensors, warning/status/mismatch entities still require live Home Assistant verification.
- The current `labos` runtime still runs `labos-mock-relay.service`, so this Home Assistant validation covered the UI-to-MQTT-to-Node-RED contract and mock relay path, not physical relay hardware.

## Zone Calibration Readiness

Status: Hardware deployment pending

- Existing `config/zones.json` now uses improved initial polygons in live 1280x720 camera-image coordinates.
- Zone numbering is from the live camera perspective, not the architectural top-down room diagram: Zone 1 bottom-left/camera-side, Zone 2 middle-right/lower-mid, Zone 3 left/mid visible working area, Zone 4 top-right, Zone 5 upper-middle, Zone 6 top-left.
- The previous top-down/room-layout interpretation was not safe for Auto and was replaced with an improved initial camera-perspective calibration.
- Approximate zone centers and sample foot-points map uniquely in software.
- Shared boundary ambiguity is documented.
- Ten-minute live model validation saw 59.20% zone-boundary uncertainty with the provisional grid.
- Ten-minute live people-count validation saw 36.32% zone-boundary uncertainty with the provisional grid.
- Live validation with the corrected slanted zones still needs to be rerun after the interrupted calibration pass.
- The new calibration remains approximate and must be verified in live occupied scenes before Auto is trusted.
- The old top-down room diagram must not be used directly for image polygon calibration; all final points must be clicked or verified in the camera frame.
- Short display-mode validation after this correction opened the live stream and confirmed `lab/vision/#` traffic only with zero observed `lab/control/+/set` messages. The current scene did not match the earlier four-person screenshot; stable count held at 3 while raw diagnostics briefly reached 4, so the four-person zone assignment still needs a matching occupied live scene to verify visually.
- Door, seated people, occlusion, and real boundaries are not physically verified.
- Do not update final zone configuration until supervised live validation passes.

## Physical Auto-Mode Readiness

Status: Not physically production-ready until supervised relay validation passes

- A short supervised Auto-mode entry/exit safety check was completed against the deployed `labos` flow.
- Earlier confusion about `mode_state` was resolved: fresh `lab/automation/mode_state = auto` does publish when captured correctly.
- Final mode was returned to `manual` successfully.
- Manual baseline stayed safe, Monitor mode produced intended states, and manual override capture/clear worked.
- The supervised Auto attempt emitted zero relay `/set` commands.
- Physical Zone 1-6 occupied Auto tests were not completed successfully because active Auto relay behavior was not observed.
- Multiple-zone occupied Auto tests were not completed successfully.
- Real relay/light/fan switching behavior, repeated-command behavior, and flicker behavior remain unverified on hardware.
- Follow-up live debug confirmed `lab/automation/mode = auto` is correct and fresh `lab/automation/mode_state = auto` does publish when captured correctly.
- In the subsequent supervised occupied-scene Auto attempt, fresh `mode_state = auto` was observed, but the AI stream still reported only `stable_count = 0`, so no intended-state scene transitions or relay commands were triggered.
- In the latest startup/shutdown validation run, Auto was exercised only for safe controller-path checks and was returned to `manual` at the end of the session.
- A controlled mock-path Auto validation on June 17, 2026 observed two relay `/set` messages on the mock path (`relay7 ON`, then `relay7 OFF`) while final mode was returned to `manual`.
- This remains mock-path validation only because `labos-mock-relay.service` is still active and no real ESP32/light/fan hardware claim was made.

## Failure-Test Readiness

Status: Hardware deployment pending

- Camera failure behavior is validated in software.
- Live camera-stop, AI-stop, MQTT-disconnect, and ESP32-restart tests are not complete.
- Relay state preservation under real hardware failure remains pending.

## Remaining Blockers

- Keep monitoring the hardened `/labcam` bridge and health-check timer during longer unattended runs.
- Retest stale-vision fallback with the live mock-relay/manual-override noise removed or better isolated.
- Reduce or eliminate upstream HEVC reference-frame decode warnings if they affect downstream analytics.
- Verify ESP32 firmware on real hardware.
- Verify Home Assistant entities.
- Complete supervised manual relay mapping.
- Complete live zone calibration.
- Complete supervised Auto-mode and failure tests.
