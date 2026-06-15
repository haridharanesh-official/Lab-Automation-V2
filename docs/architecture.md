# Architecture and Operation

`Camera -> AI PC -> labos/v2/vision/# -> Mosquitto -> Node-RED -> labos/v2/relay/+/set -> ESP32`

Home Assistant uses MQTT for manual switches, mode selection, and monitoring. The AI PC has no API capable of relay command publication. Node-RED validates complete reports, rejects stale sequence numbers, applies two-empty-report shutdown, calculates fan OR rules, and deduplicates against confirmed relay state.

## Recovery

1. Leave or return the mode to Manual.
2. Restore camera, broker, Node-RED, or ESP32 service.
3. Confirm heartbeats and state topics.
4. Use Monitor mode and simulator reports to validate decisions.
5. Resume Auto only under supervision.

