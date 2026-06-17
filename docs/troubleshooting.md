# Troubleshooting

## Vision Publisher Fails to Start
- Ensure the RTSP camera stream is active (`rtsp://hari:8554/labcam`).
- Check that the `.venv` is activated and `lap` and `ultralytics` are installed.
- Ensure the model path in `config/config.yaml` points to a valid weights file.

## Zero Relay Commands Being Published
- If the system is in `monitor` or `manual` mode, zero commands being published is the *expected behavior*.
- Use `mosquitto_sub` to verify the intended states:
  `mosquitto_sub -h labos -v -t 'lab/automation/intended_state'`
- The live runtime uses `lab/...` topics, not the old written `labos/v2/...` namespace.
- In Auto mode, zero new relay commands can also be correct when the confirmed relay states already match the desired state. Check:
  `mosquitto_sub -h labos -v -t 'lab/control/+/state'`

## Camera Disconnects
- The AI PC publishes a `healthy: false` status. Node-RED will trap the condition and freeze all relays.
- To recover, restore the camera feed. The AI PC will resume stable window generation after 60 seconds of clean data.

## HA Dashboard Shows 401 Unauthorized
- The MQTT broker authentication might be misconfigured, or the web UI tokens expired.
- Use a physical browser session to re-authenticate with the server. Local AI agents cannot verify the dashboard.

## Duplicate Home Assistant Relay Entities
- The final retained discovery topics should be `homeassistant/switch/labos_*/config`.
- Stale generic discovery topics such as `homeassistant/switch/lab_relay*/config` should not remain.
- Check retained discovery:
  `mosquitto_sub -h labos -v -C 30 -t 'homeassistant/switch/+/config'`
- Clear a stale retained config only after confirming it is not the active final entity:
  `mosquitto_pub -h labos -t homeassistant/switch/lab_relay1/config -r -n`

## Relay Ack Monitor Parse Errors
- If `labos-relay-ack-monitor.service` logs errors like `invalid literal for int() with base 10: 'set'`, the parser is reading the wrong topic segment.
- For topics like `lab/control/relay3/set`, the relay ID is in `topic.split("/")[2]`, not index `3`.
- The live `labos` fix was applied on June 17, 2026 with backup at `/home/labos/labos-v2-backups/live-fixes-20260617-142445/relay_ack_monitor.py`.
