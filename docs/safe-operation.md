# Safe Operation Guidelines

Lab Automation v2.0 is designed to fail safe.

## Default Mode
- The system defaults to **Manual** mode.
- In Manual mode, the AI publisher generates telemetry but does not actuate any relays. Node-RED ignores all automated commands.

## Auto Mode Strict Enforcements
- Before shutting off a relay, Node-RED requires **two consecutive empty reports** spanning a full 2-minute cycle.
- This prevents people from being left in the dark due to a momentary camera occlusion or false negative.
- The AI PC must maintain a continuous heartbeat with the MQTT broker. If the heartbeat drops, the relays hold their last known state.

## Physical Safety Checks
- Physical tests must be completed using the `Monitor` mode.
- In `Monitor` mode, Node-RED parses zone maps into `intended` relay states but physically outputs `0` commands to the `labos/v2/relay/+/set` topics.

## Validation Status
Currently, physical live validation is **Blocked**. The system has passed mathematical verification and static analysis, but has not yet undergone supervised human-in-the-loop tests. **DO NOT enable Auto mode physically** until a supervisor clears the physical zone-walk and Home Assistant web UI dashboard.
