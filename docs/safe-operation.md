# Safe Operation Guidelines

Lab Automation v2.0 is designed to fail safe.

## Default Mode
- The system defaults to **Manual** mode.
- In Manual mode, the AI publisher generates telemetry but does not actuate any relays. Node-RED ignores all automated commands.

## Auto Mode Strict Enforcements
- Before shutting off controlled loads for an empty room, Node-RED requires 60 continuous seconds of `stable_count = 0`.
- This prevents people from being left in the dark due to a momentary camera occlusion or false negative.
- The AI PC must maintain a continuous heartbeat with the MQTT broker. If the heartbeat drops, the relays hold their last known state.
- Current Auto decisions are people-count based. Node-RED reads `lab/vision/people_count.stable_count`; zone counts are provisional diagnostics and do not drive relays.
- Current live hardware is 8-relay final lab wiring. Automation controls only relays `2,3,4,6,7,8`; relays `1` and `5` are spare.
- HIGH_STAGE latches after `4+` people so loads do not flicker when counts move between `3` and `4`. The latch resets only after 60 continuous seconds of confirmed empty room.
- People-count rules: `0` people -> delayed OFF; `1` person -> both lights ON; `2-3` people -> both lights + Fan 1 + Fan 4 ON; `4+` people -> both lights + all fans ON.

## Physical Safety Checks
- Physical tests must be completed using the `Monitor` mode.
- In `Monitor` mode, Node-RED parses the debounced total people count into `intended` relay states but physically outputs `0` commands to `lab/control/+/set`.

## Validation Status
Currently, physical live validation is **Blocked**. The system has passed mathematical verification and static analysis, but has not yet undergone supervised human-in-the-loop tests. **DO NOT enable Auto mode physically** until a supervisor clears the physical zone-walk and Home Assistant web UI dashboard.
