# MQTT Topics

All topics are isolated below `labos/v2/`.

- Vision: `vision/status`, `vision/heartbeat`, `vision/zones/report`, `vision/zone/{1..6}/count`
- Automation: `automation/mode/set`, `automation/mode/state`, `automation/status`, `automation/decision`, `automation/warning`
- Relay: `relay/{1..10}/set`, `relay/{1..10}/state`
- Controller: `controller/status`

Rules: vision may publish only under `labos/v2/vision/#`; relay `/set` commands must never be retained; Node-RED alone may automatically publish `/set`; retained mode state defaults to Manual.

