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
- [x] Harden camera bridge against intermittent `/labcam` `404` periods during upstream interruptions.
- [x] Verify `mediamtx.service` starts on boot on `hari`.
- [x] Verify `labos-camera-bridge.service` starts on boot on `hari`.
- [x] Verify `labcam-healthcheck.timer` is enabled on `hari`.

## Room mapping
- [x] Verified `config/zones.json`.
- [x] Six-zone polygon mapping works with bottom-centre assignment.
- [x] Applied rough slanted perspective zones from the user-marked back-camera reference.
- [x] Corrected Zone 1/Zone 2 split so Zone 1 remains bottom-right and Zone 2 owns bottom-middle.
- [x] Filled the bottom-right empty area into Zone 1 with a clean shared Zone 1/Zone 2 boundary.
- [x] Mappings marked provisional until physical tests pass.
- [ ] Reduce live zone-boundary uncertainty through final supervised calibration.

## AI publisher
- [x] Verified one-minute stable reports.
- [x] Verified 10-second heartbeat.
- [x] Verified camera failure clears windows and preserves states.
- [x] Verified unsafe MQTT topics are rejected.
- [x] Verified `start_lab_automation.ps1` headless live startup/shutdown path against the real broker and RTSP stream.
- [x] Verified `start_lab_automation.ps1 -Display` live startup/shutdown path against the real broker and RTSP stream.
- [x] Fixed startup PID metadata parsing so older runs without a `display` field no longer crash display mode.
- [x] Retargeted AI PC live publisher defaults to `lab/vision/people_count`, `lab/vision/status`, `lab/vision/source_status`, and `lab/vision/heartbeat`.
- [x] Confirmed AI publisher still refuses `lab/control/#`, relay, `/set`, and `/command` topics.
- [x] Camera retry Monitor validation imported no MQTT client and published zero reports or relay `/set` commands.
- [x] Ten-minute live model validation used MQTT disabled and published zero relay `/set` commands.
- [x] Ten-minute live people-count validation used MQTT disabled and published zero relay `/set` commands.

## Node-RED
- [x] Import updated priority-safety flow on live Node-RED.
- [x] Confirm current deployed `labos` runtime mode is Manual.
- [x] Monitor MQTT test observed zero relay `/set` commands.
- [x] Verified deployed `labos` Node-RED receives and processes `lab/vision/people_count`.
- [x] Verified Manual mode emits zero relay `/set` commands during live AI publishing.
- [x] Repo flow now models priority order: manual override > timetable fallback > healthy people-count automation.
- [x] Repo flow now documents manual override clear topic and timetable fallback windows.
- [x] Verified stale or unhealthy vision no longer forces `mode_state` back to `manual`.
- [x] Verified `auto` + stale vision keeps `mode_state = auto` and moves `priority_state` to fallback behavior.
- [x] Verified live `lab/...` diagnostics after deployment: `mode_state`, `manual_override_state`, `priority_state`, `vision_health`, `warning`, `intended_state`.
- [x] Verified live outside-window fallback behavior lands on `TIMETABLE_HOLD` with zero relay `/set` commands.
- [x] Verified live manual override capture and clear on `labos`.
- [x] Modernized the legacy `labos-automation.service` bridge on `labos` into a passive observer so it no longer republishes `lab/automation/mode` or relay `/set`.
- [x] Modernized `labos-system-health.service` to observe the current `lab/vision/people_count` JSON topic instead of the old `/state` count.
- [ ] Verify live inside-window timetable fallback during `08:30-12:30` or `13:00-16:30`.
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
- [x] Verify mode selector metadata and MQTT contract.
- [x] Updated the live `labos` Home Assistant discovery publisher so the mode selector uses `state_topic = lab/automation/mode_state` and options `manual`, `monitor`, `auto`.
- [x] Confirm stale vision no longer forces Node-RED `mode_state` back to `manual`.
- [x] Reconfirmed fresh live `mode_state` transitions for `manual`, `monitor`, and `auto` on June 17, 2026.
- [ ] Verify health, warning, status, and mismatch sensors.

## Testing
- [x] Run all existing tests.
- [x] Static validation passed.
- [x] Validate live AI -> MQTT -> deployed Node-RED Manual-mode path.
- [x] Validate live simulation-only priority-safety path with final mode returned to Manual.
- [x] Resolve live `lab/automation/mode` to active Auto behavior confirmation on `labos`.
- [x] Complete 10-15 minute empty-lab Monitor validation with repeated `stable_count = 0`, zero false positives, and zero relay `/set` commands.
- [ ] Complete full supervised Auto-mode validation with occupied-scene relay changes.
- [ ] Complete supervised occupied-scene Auto validation with non-zero stable counts observed on live `lab/vision/people_count`.
- [x] Complete supervised Auto-mode entry/exit safety check with final mode returned to Manual.
- [ ] Complete a cleaner live stale-vision fallback validation without noisy mock-relay/manual-override diagnostics.
- [ ] Complete live failure tests.
