# Architecture and Operation

`Camera -> AI PC -> lab/vision/# -> Mosquitto -> Node-RED -> lab/control/relayX/set -> ESP32`

Home Assistant uses MQTT for manual switches, mode selection, and monitoring. The AI PC has no API capable of relay command publication. Node-RED owns the relay path and now implements a strict priority order: Manual preserve first, stale-vision preserve-state second, Monitor diagnostics-only third, and healthy people-count Auto fourth. The flow rejects stale vision, preserves state on failure, applies delayed zero/off behavior, and deduplicates against confirmed relay state plus correction memory.

## Recovery

1. Leave or return the mode to Manual.
2. Restore camera, broker, Node-RED, or ESP32 service.
3. Confirm heartbeats and state topics.
4. Use Monitor mode and simulator reports to validate decisions.
5. Resume Auto only under supervision.
