# Current Status

**Date**: June 17, 2026

## Overview
Lab Automation v2.0 is currently in the **validation phase**. Software validation is complete, and the Node-RED priority safety flow is deployed on the `labos` runtime.

## Recent Achievements
- **Camera Stream**: `rtsp://hari:8554/labcam` is active and stable.
- **AI Publisher**: Correctly restricted to publishing `lab/vision/#`. It successfully drops all control commands.
- **Windows Startup Wrapper**: Headless and display startup/shutdown were validated live against `labos:1883` and `rtsp://hari:8554/labcam`. The display metadata bug was fixed by making PID-file parsing tolerant of older entries that do not yet contain the `display` flag.
- **Empty-Lab Validation**: Ran for ~11 minutes in Monitor mode with:
  - 0 false positives
  - 0 relay `/set` commands issued
- **Tests**: 27/27 tests passing.
- **Node-RED**: Strict priority-safety flow deployed on `labos`, consuming `lab/...` topics.
- **Mode Handling**: Auto selection now stays `auto` even when vision becomes stale; stale vision changes only `priority_state` to timetable fallback/hold behavior.
- **Home Assistant**: The live selector metadata on `labos` now exposes `manual`, `monitor`, and `auto`, and its retained discovery state topic is `lab/automation/mode_state`.
- **Mode Authority**: The legacy `labos-automation.service` bridge was modernized into a passive observer, so it no longer republishes `lab/automation/mode` or relay `/set` topics.
- **Relay Command Authority**: The live relay-ack monitor no longer injects relay OFF commands; Node-RED is now the only live relay-command publisher in the validated path.
- **Live Runtime Caveat**: `labos` is still running `labos-mock-relay.service`, so the latest end-to-end authority validation covered the control path and MQTT contract, not physical ESP32 load switching.
- **Latest Auto Gate Result**: Live mode transitions `manual -> monitor -> auto -> manual` were reconfirmed over MQTT, but the stale-vision fallback path still needs a cleaner live validation before leaving the system in Auto unattended.

## Safe Mode Enforcements
- **Final Safe Mode**: `manual`. The system returns to this mode upon any deployment or recovery.
- **Relay Commands**: Only Node-RED can publish to `lab/control/#`. AI PC is strictly a vision telemetry publisher.

## Pending Real-World Validation
The system is **not production-ready** until we complete:
1. Occupied-scene Monitor validation when a person is visible.
2. Supervised Auto validation with people in the room.
3. Physical light/fan mapping confirmation with the ESP32.

---
*If you are new to this codebase, please review the [Project Explained for Beginners](file:///c:/Users/prith/Downloads/Lab%20Automation%20v2.0/docs/project-explained-for-beginners.md) guide.*
