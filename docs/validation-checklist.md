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
- [x] Recalibrated zones using live camera-image perspective rather than the architectural top-down room diagram.
- [x] Camera-perspective numbering is now: Zone 1 bottom-left/camera-side, Zone 2 middle-right/lower-mid, Zone 3 left/mid working area, Zone 4 top-right, Zone 5 upper-middle, Zone 6 top-left.
- [x] Added tests for representative 1280x720 camera-perspective points and out-of-zone assignment.
- [x] Ran short display-mode live check after camera-perspective update; AI published only `lab/vision/#`, no relay `/set` messages were observed, and final mode was returned to `manual`.
- [x] Ran follow-up AI PC -> `labos` validation after camera-perspective update. `labos` received debounced `lab/vision/people_count` (`stable_count = 4`, `zone_counts = [0,2,2,0,0,0]` in the initial live capture), fresh status/source/heartbeat, and Node-RED accepted the count.
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
- [x] Split raw detection diagnostics to `lab/vision/raw_people_count` while keeping `lab/vision/people_count` debounced for HA and Node-RED.
- [x] Added anti-flicker logic so brief missed detections and camera uncertainty do not immediately publish false zero.
- [x] Updated live display overlay to show current zone counts, stable zone counts, published count, window sample count, seconds until report, foot-point markers, assigned zones, and OUT markers.
- [x] Inspected `labos` for competing `lab/vision/people_count` publishers; active legacy bridge and health monitor were subscribers/observers, not competing publishers.
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
- [x] Verified Monitor mode processes live people count into intended-state diagnostics with zero relay `/set` commands.
- [x] Performed a short safe Auto logic check: fresh `mode_state = auto` confirmed, people-count path selected, final mode returned to `manual`, and no relay `/set` messages were captured during the short check.
- [x] Locked current Auto behavior to total people count only. Node-RED reads `lab/vision/people_count.stable_count`; `zone_counts` remains diagnostic/provisional and is not used for relay decisions.
- [x] Added tests for people-count Auto rules: `0` delayed OFF, `1` both lights, `2-3` both lights + Fan 1/Fan 4, `4+` both lights + all fans.
- [x] Added selectable AI counting modes: `total-count` requires no zones and shows clean display; `zone-count` requires `config/zones.json` and shows full debug overlays.
- [x] Added tests proving total-count display does not use debug overlay and zone-count display keeps it.
- [x] Added retained Node-RED automation status publishing in the repo flow: `lab/automation/status = online`.
- [x] Repo flow now models priority order: Manual preserve > stale-vision preserve-state > Monitor diagnostics > healthy people-count Auto.
- [x] Repo flow now documents manual override clear topic and empty-room delay behavior.
- [x] Verified stale or unhealthy vision no longer forces `mode_state` back to `manual`.
- [x] Verified `auto` + stale vision keeps `mode_state = auto` and moves `priority_state` to fallback behavior.
- [x] Verified live `lab/...` diagnostics after deployment: `mode_state`, `manual_override_state`, `priority_state`, `vision_health`, `warning`, `intended_state`.
- [x] Verified live outside-window fallback behavior lands on `TIMETABLE_HOLD` with zero relay `/set` commands.
- [x] Verified live manual override capture and clear on `labos`.
- [x] Modernized the legacy `labos-automation.service` bridge on `labos` into a passive observer so it no longer republishes `lab/automation/mode` or relay `/set`.
- [x] Modernized `labos-system-health.service` to observe the current `lab/vision/people_count` JSON topic instead of the old `/state` count.
- [ ] Verify live stale-vision preserve-state behavior with zero relay `/set` commands.
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
- [x] Verified the MQTT topic feeding HA People Count: `lab/vision/people_count`. Direct dashboard/API value read was not completed because unauthenticated HA API access returned `401 Unauthorized`.
- [ ] Directly click through the Home Assistant UI selector for `manual -> monitor -> auto -> manual`.
- [ ] Verify health, warning, status, and mismatch sensors.

## Testing
- [x] Run all existing tests.
- [x] Static validation passed.
- [x] Validate live AI -> MQTT -> deployed Node-RED Manual-mode path.
- [x] Validate live simulation-only priority-safety path with final mode returned to Manual.
- [x] Resolve live `lab/automation/mode` to active Auto behavior confirmation on `labos`.
- [x] Complete 10-15 minute empty-lab Monitor validation with repeated `stable_count = 0`, zero false positives, and zero relay `/set` commands.
- [x] Complete live monitor-mode simulator validation with zero relay `/set` commands.
- [x] Complete live auto-mode mock-path simulator validation with final mode returned to Manual.
- [x] Complete supervised people-count Auto smoke validation with non-zero `stable_count = 4`, `FOUR_PLUS` intended state, final mode returned to Manual, and no repeated relay command spam.
- [ ] Complete full supervised Auto-mode validation with deliberate occupied-scene relay transitions for `1`, `2-3`, `4+`, and empty-delay OFF cases.
- [x] Complete supervised occupied-scene Auto validation with non-zero stable counts observed on live `lab/vision/people_count`.
- [x] Complete supervised Auto-mode entry/exit safety check with final mode returned to Manual.
- [ ] Complete a cleaner live stale-vision fallback validation without noisy mock-relay/manual-override diagnostics.
- [ ] Complete live failure tests.

## Final June 17 Live Finisher
- [x] Confirmed `labos-mock-relay.service` is disabled and inactive.
- [x] Confirmed stale generic HA discovery topics `homeassistant/switch/lab_relay*/config` are absent.
- [x] Confirmed final HA discovery topics `homeassistant/switch/labos_*/config` remain and use `lab/control/relayX/set` plus `lab/control/relayX/state`.
- [x] Confirmed AI `lab/vision/people_count` payload contains `stable_count`, `counting_mode = total-count`, and `zone_counts = null`.
- [x] Confirmed Monitor mode produced `0` relay `/set` commands over at least 30 seconds.
- [x] Confirmed Manual mode produced `0` relay `/set` commands while AI counts continued.
- [x] Applied live-only relay ack monitor parser fix on `labos`; repo does not contain that service source.
- [x] Ran final deployment gate in `total-count` mode: Monitor passed with `0` relay `/set` commands and Auto reached `mode_state = auto`, `priority_state = PEOPLE_COUNT`, and `FOUR_PLUS`.
- [ ] Leave Auto enabled as the final deployed mode. Blocked on missing `lab/control/relay4/state` feedback during final Auto capture.
- [x] Confirm Fan 3 / relay4 feedback publishes on `lab/control/relay4/state` after a direct supervised command: `relay4/set ON -> relay4/state ON`, `relay4/set OFF -> relay4/state OFF`.
- [x] Confirm Home Assistant discovery maps Fan 3 to `lab/control/relay4/set` and `lab/control/relay4/state`.
- [x] Rerun Auto after relay4 feedback was restored; live `stable_count = 2` selected `TWO_THREE`, relay4 remained OFF with feedback present, and final mode returned to Manual.
- [x] Fix stale retained warning behavior so healthy vision publishes retained `lab/automation/warning = none`.
- [x] Rerun a supervised `4+` Auto scene where Auto itself commands relay4/Fan 3 ON: observed `lab/control/relay4/set ON` followed by `lab/control/relay4/state ON`.
- [x] Leave Auto enabled after final supervised gate passed.
- [x] Fix relay power-loss recovery: `lab/control/status offline` clears known relay feedback/last commands, and `online` in Auto with healthy non-zero count resyncs desired relay state even when `stable_count` did not change.
- [x] Validate controlled relay reconnect simulation: `stable_count = 7` produced one non-retained ON command each for relays `2,3,4,6,7,8`; matching state feedback returned; repeated `online` produced `0` relay `/set`.
- [x] Add Auto-only periodic feedback reconciliation: every controller tick, compare desired state to `lab/control/relayX/state`, resend only missing/mismatched non-retained commands, and keep Manual/Monitor at `0` physical relay commands.
- [x] Validate periodic mismatch correction: forced `lab/control/relay2/state OFF` while desired `FOUR_PLUS` required ON; Node-RED sent one `lab/control/relay2/set ON`, feedback returned ON, and no repeated command spam followed.
- [x] Add repo tests for immediate Auto-entry recompute, Manual preserve/no-AI-command behavior, Monitor zero relay commands, continuous empty-delay OFF, positive-count empty-timer reset, Auto relay reconnect/resync, retained feedback mismatch correction, stale-vision preserve-state behavior, and one-shot correction/no-spam behavior.
- [x] Confirm current retained live mapping is still the 8-channel final lab wiring: relays `1` and `5` spare; controlled loads on relays `2,3,4,6,7,8`.
- [x] Add repo tests for 8-relay LOW_STAGE/HIGH_STAGE behavior, high-load latch retention for later counts `1-3`, 60-second zero reset, and spare relay exclusion.
- [ ] Redeploy the June 18 priority fix to live Node-RED after `labos:1880` admin access is reachable.
- [ ] Rerun live Manual, Monitor, Auto-entry, empty-delay, relay reconnect, and no-spam validation after relay controller status returns `online`.
- [ ] Continue longer supervised observation for empty-delay OFF, camera/AI failure fallback, MQTT interruption, ESP32 restart, and no-flicker behavior.
