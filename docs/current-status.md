# Current Status

**Status: People-count Auto deployed under supervision; zone-count calibration still pending**

The AI Publisher, Node-RED logic, and ESP32 firmware have all passed unit tests and simulated checks.
On June 17, 2026, the live `labos` runtime was inspected over SSH with physical supervision in the lab. The final runtime namespace is `lab/...`; older `labos/v2/...` topics are historical only.

## What is Working
- `start_lab_automation.ps1 -Display` launches successfully.
- Pytest suite (`pytest tests/`) passes 100% (49 tests), proving selectable AI counting modes, zone-mapping logic, people-count Auto rules, Node-RED monitor mode behavior, and safety namespaces.
- Simulated reports confirm that when `lab/automation/mode` is `monitor`, Node-RED correctly processes zone occupancy to intended relay states but sends 0 physical `/set` commands.
- Current Auto logic is people-count based, not zone based. Node-RED uses `lab/vision/people_count.stable_count` for stages: `0` delayed OFF, `1` both lights, `2-3` both lights plus Fan 1/Fan 4, and `4+` both lights plus all fans.
- AI publisher modes are now explicit: `total-count` is usable now for Auto and shows clean display footage; `zone-count` is available for debug/calibration and shows full boxes/zones/foot-point overlays.
- Zone mapping remains provisional and is used for display/debug validation only until zone-by-zone live validation passes and Node-RED is intentionally switched to zone-count automation.
- Live `labos` relay command path was confirmed from Home Assistant MQTT discovery: commands use `lab/control/relayX/set` with `ON`/`OFF`; states use `lab/control/relayX/state` with `ON`/`OFF`.
- `labos-mock-relay.service` is stopped and disabled.
- Stale generic Home Assistant discovery topics `homeassistant/switch/lab_relay*/config` were removed; only the final `homeassistant/switch/labos_*/config` switch discovery set remained in the verified broker snapshot.
- The live-only helper `/home/labos/labos-edge/services/safety-layer/relay_ack_monitor.py` was fixed on `labos` to parse `lab/control/relay3/set` as relay 3 instead of trying to parse `set` as a relay number. The live backup is `/home/labos/labos-v2-backups/live-fixes-20260617-142445/relay_ack_monitor.py`.
- Final Monitor validation observed `stable_count = 4`, `mode_state = monitor`, `intended_state = FOUR_PLUS`, and `0` relay `/set` messages over a 30-second capture.
- Final supervised Auto smoke validation observed `mode_state = auto`, `stable_count = 4`, `priority_state = PEOPLE_COUNT`, and `intended_state = FOUR_PLUS` for relays `2,3,4,6,7,8 = ON`. No new relay `/set` commands were needed in the final Auto window because the retained/known relay states already matched the desired ON state.
- Final Manual isolation validation observed `mode_state = manual`, continuing accepted AI counts, and `0` relay `/set` messages over a 20-second capture.
- Final deployment attempt on June 17, 2026 initially kept the system in `manual` because `lab/control/relay4/state` feedback was missing from the Auto capture even though the `FOUR_PLUS` decision includes relay 4 / Fan 3. Follow-up relay4 isolation proved the feedback path is alive: manual `lab/control/relay4/set ON` produced `lab/control/relay4/state ON`, and `OFF` produced `state OFF`. HA discovery confirms Fan 3 uses `lab/control/relay4/set` and `lab/control/relay4/state`.
- Follow-up Auto rerun saw live `stable_count = 2`, so Node-RED correctly selected the `TWO_THREE` rule with relay4/Fan 3 OFF. Relay4 state feedback was present as `lab/control/relay4/state OFF`, Monitor still produced `0` relay `/set` commands, and no repeated command spam was observed.
- Final clear-and-deploy pass fixed stale retained warning behavior: healthy vision now publishes retained `lab/automation/warning = none`; unhealthy/stale vision publishes a retained fallback warning.
- Final 4+ supervised Auto gate passed: with relay4/Fan 3 first forced OFF in Manual and overrides cleared, live `stable_count = 4` selected `FOUR_PLUS`; Auto emitted exactly one relay command, `lab/control/relay4/set ON`, and feedback arrived as `lab/control/relay4/state ON`. No repeated identical command spam was observed, and `lab/automation/warning` remained `none`.
- Final deployed mode after this pass is `auto`, per supervised deployment request.
- June 18 relay power-loss recovery fix deployed: when `lab/control/status` reports `offline`, Node-RED now clears cached relay feedback and last-command state; when it reports `online` again in Auto with healthy non-zero people count, Node-RED recomputes the desired state and sends one reconciliation command per controlled relay that needs restoration.
- Controlled live validation simulated `offline -> online` with fresh healthy `stable_count = 7`; Auto recomputed `FOUR_PLUS`, published one non-retained ON command each for relays `2,3,4,6,7,8`, received matching state feedback, and a repeated `online` status produced `0` relay `/set` commands.
- Follow-up live issue showed Auto was healthy with `stable_count = 7`, but all controlled relays were held OFF by `manual_override_state`. Root cause: Auto-mode relay OFF feedback after power loss had been captured as manual overrides. The flow now captures manual overrides only in Manual mode; Auto feedback mismatches are corrected by automation instead of frozen.
- After clearing overrides and redeploying the fix, live Auto showed `manual_override_state {}`, `priority_state = PEOPLE_COUNT`, `stage = FOUR_PLUS`, and all controlled relay states ON.
- Periodic Auto feedback reconciliation is now deployed. Every controller tick, currently about 10 seconds, Node-RED compares the desired people-count relay state with `lab/control/relayX/state` and sends only missing/mismatched non-retained corrections. Controlled live validation forced `relay2/state OFF` while `FOUR_PLUS` required relay 2 ON; the next tick sent one `lab/control/relay2/set ON`, feedback returned ON, and later ticks did not spam repeated commands.

## Blockers
- **Physical Walk Test**: Requires a human to walk through zones 1-6 physically in front of the camera before zone-count automation can be trusted.
- **HA Dashboard Verification**: MQTT discovery and command topics are verified, and the user reported Home Assistant can physically control all fans/lights. Direct API/dashboard reads still require an authenticated Home Assistant session.
- **Zone-count Calibration**: Production automation is currently people-count based. Zone-count mode remains available for debugging/calibration but is not the deployed Auto decision source.
- **Long-run Production Gate**: Continue supervised observation for empty-delay OFF, camera-failure hold/fallback, MQTT interruption, ESP32 restart behavior, and longer no-flicker operation under changing occupancy.
