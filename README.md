# Lab Automation v2.0

Local-first six-zone lab automation for six lights and four fans. Vision publishes telemetry only; Node-RED is the sole automatic relay-command authority.

## Safety Defaults

- Node-RED defaults to `manual`.
- Vision publisher accepts only `labos/v2/vision/#`.
- Monitor mode calculates intended states but sends zero relay commands.
- Relay `/set` messages are non-retained.
- Camera/AI failure preserves current relay states.
- ESP32 initializes every active-LOW relay OFF.

## Layout

- `ai-pc/`: zone/report/vision logic and safe simulator
- `node-red/flows.json`: importable automation controller flow
- `esp32/`: ten-relay controller firmware
- `home-assistant/mqtt.yaml`: MQTT entities
- `config/`: secret-free example configuration and initial zones
- `tests/`: software safety verification
- `docs/`: architecture, topics, validation, troubleshooting, readiness

## Quick Start

1. Install Python 3.11, Mosquitto, Node-RED, and Home Assistant.
2. Run `.\setup_windows.ps1`.
3. Copy/edit `config\config.yaml`; never commit secrets.
4. Calibrate zones: `.\calibrate_zones.ps1 -Image path\to\empty-lab.jpg`.
5. Import `node-red\flows.json`, verify mode is `manual`, and configure broker credentials.
6. Flash ESP32 only during supervised relay testing.
7. Run `py -3.11 -m pytest`.
8. Run Monitor-mode simulations before considering Auto.

Do not enable physical Auto mode until every item in `docs/validation-checklist.md` is supervised and verified.

