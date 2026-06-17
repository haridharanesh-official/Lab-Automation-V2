# Troubleshooting

## Vision Publisher Fails to Start
- Ensure the RTSP camera stream is active (`rtsp://hari:8554/labcam`).
- Check that the `.venv` is activated and `lap` and `ultralytics` are installed.
- Ensure the model path in `config/config.yaml` points to a valid weights file.

## Zero Relay Commands Being Published
- If the system is in `monitor` or `manual` mode, zero commands being published is the *expected behavior*.
- Use `mosquitto_sub` to verify the intended states:
  `mosquitto_sub -h labos -t 'labos/v2/automation/decision'`

## Camera Disconnects
- The AI PC publishes a `healthy: false` status. Node-RED will trap the condition and freeze all relays.
- To recover, restore the camera feed. The AI PC will resume stable window generation after 60 seconds of clean data.

## HA Dashboard Shows 401 Unauthorized
- The MQTT broker authentication might be misconfigured, or the web UI tokens expired.
- Use a physical browser session to re-authenticate with the server. Local AI agents cannot verify the dashboard.
