# Validation Checklist

## Safety Enforcements
- [x] Keep system in Manual/Monitor mode.
- [x] Do not publish relay `/set` commands during development.
- [x] Auto mode is not enabled physically.
- [x] No secrets, videos, large datasets, or weights are committed.
- [x] Original models and datasets are preserved.

## Vision and model
- [x] Keep `backcam_yolov8s_improved_v3_hardfp.pt` as production-safe model.
- [x] Validated candidate against duplicate boxes, missed people, false positives, etc.

## Room mapping
- [x] Verified `config/zones.json`.
- [x] Six-zone polygon mapping works with bottom-centre assignment.
- [x] Mappings marked provisional until physical tests pass.

## AI publisher
- [x] Verified one-minute stable reports.
- [x] Verified 10-second heartbeat.
- [x] Verified camera failure clears windows and preserves states.
- [x] Verified unsafe MQTT topics are rejected.

## Node-RED
- [x] Verified Manual, Monitor, Auto logic.
- [x] Monitor sends zero relay commands.
- [x] Auto deduplicates relay commands and requires two empty reports before OFF.
- [x] Validated relay mapping.

## ESP32
- [x] Ten-relay active-LOW firmware.
- [x] GPIO 5 must not be used.
- [x] Relay 1 uses GPIO 33.
- [x] Safe OFF startup, MQTT reconnect, watchdog, state publishing.
- [x] Home Assistant discovery integration.

## Home Assistant
- [x] Verified MQTT config for ten relays, six zones, mode selector, health, warnings.

## Testing
- [x] Run all existing tests.
- [x] Static validation passed.
