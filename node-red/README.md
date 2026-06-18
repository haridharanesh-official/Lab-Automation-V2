# Node-RED Flow Notes

The repo flow in [flows.json](/C:/Users/prith/Downloads/Lab%20Automation%20v2.0/node-red/flows.json) now targets the current deployed `labos` runtime MQTT contract:

- vision input under `lab/vision/...`
- automation state under `lab/automation/...`
- relay control under `lab/control/...`

Priority order implemented in the repo flow:

1. Manual mode: preserve current relay state and send no AI relay commands.
2. Stale/unhealthy vision: preserve current/last-known relay state and publish a warning.
3. Monitor mode: compute intended state diagnostics and send zero physical relay commands.
4. Auto mode with healthy vision: compute from latest debounced people count and correct only missing/mismatched relay feedback.

Current Auto behavior is people-count-only. The flow reads `lab/vision/people_count.stable_count` and ignores `zone_counts` for relay decisions until zone calibration is physically validated.

The retained diagnostic topic `lab/automation/count_source` should be `total-count`. `zone-count` automation remains a future source mode only; the AI can publish zone counts for calibration, but this flow does not use them for relay decisions yet.

The flow also publishes retained `lab/automation/status = online` so Home Assistant does not keep a stale `offline` automation status.

Stage rules:
- `0` people: preserve current Auto stage for 60 continuous seconds, then controlled relays `2,3,4,6,7,8` OFF and high-load latch reset
- `1-3` people with latch inactive: `LOW_STAGE`, relays `2,3,6,7` ON and relays `4,8` OFF
- `4+` people: `HIGH_STAGE`, relays `2,3,4,6,7,8` ON and high-load latch active
- after `HIGH_STAGE`, counts `1-3` stay in `HIGH_STAGE` until 60 continuous seconds of empty room

Current live hardware is 8-channel final lab wiring. Relay `7` is Light 1, relay `2` is Light 2, relays `3,8,4,6` are Fans 1-4, and relays `1` and `5` are spares. Automation must never command spares `1` and `5`. Ten-relay support is future planned only.

Manual override clear topic:

- `lab/automation/manual_override/clear`

Do not deploy this updated repo flow onto `labos` without first backing up the live flow and validating the change in Monitor mode.

June 18 priority fix:
- Auto entry immediately recomputes from the latest healthy `stable_count`.
- Empty room must remain continuously zero for `60000` ms before OFF commands are allowed.
- High-load latch prevents flicker when counts move between `3` and `4`.
- Relay reconnect and periodic reconciliation correct missing/mismatched feedback once per observed feedback condition.
- Stale/unhealthy vision sends zero relay commands.
