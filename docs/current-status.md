# Current Status

**Status: Awaiting physical validation and dashboard confirmation**

The AI Publisher, Node-RED logic, and ESP32 firmware have all passed unit tests and simulated checks.
The live zone walk test and Home Assistant dashboard verification are currently blocked because the validation requires a physical human presence in the lab and access to the web UI, which are not currently accessible from the AI automation context.

## What is Working
- `start_lab_automation.ps1 -Display` launches successfully.
- Pytest suite (`pytest tests/`) passes 100% (49 tests), proving selectable AI counting modes, zone-mapping logic, people-count Auto rules, Node-RED monitor mode behavior, and safety namespaces.
- Simulated reports confirm that when `lab/automation/mode` is `monitor`, Node-RED correctly processes zone occupancy to intended relay states but sends 0 physical `/set` commands.
- Current Auto logic is people-count based, not zone based. Node-RED uses `lab/vision/people_count.stable_count` for stages: `0` delayed OFF, `1` both lights, `2-3` both lights plus Fan 1/Fan 4, and `4+` both lights plus all fans.
- AI publisher modes are now explicit: `total-count` is usable now for Auto and shows clean display footage; `zone-count` is available for debug/calibration and shows full boxes/zones/foot-point overlays.
- Zone mapping remains provisional and is used for display/debug validation only until zone-by-zone live validation passes and Node-RED is intentionally switched to zone-count automation.

## Blockers
- **Physical Walk Test**: Requires a human to walk through zones 1-6 physically in front of the camera.
- **HA Dashboard Verification**: Requires visual confirmation on the Home Assistant web interface, as the API returned 401 Unauthorized.
- **Service Verification**: `systemctl` commands on `labos` and `hari` could not be executed due to SSH limitations/unavailability from this environment.
