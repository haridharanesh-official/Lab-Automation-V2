# Lab Automation v2.0

An AI-driven, multi-zone room automation system using YOLOv8, Home Assistant, Node-RED, and ESP32.

## Current Status

- Software validation complete
- Hardware deployment pending
- Not physically production-ready until supervised relay validation passes

Do not enable physical Auto mode until live camera, MQTT, ESP32 relay, Node-RED, Home Assistant, zone calibration, supervised Auto-mode, and failure tests all pass on real hardware.

## Setup Instructions

### 1. Python Environment (AI PC)
```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -e .
pytest tests/
```

### 2. Microcontroller (ESP32)
1. Open `esp32/lab_automation_v2/lab_automation_v2.ino` in Arduino IDE or PlatformIO.
2. Update `WIFI_SSID`, `WIFI_PASSWORD`, and `MQTT_HOST` with your credentials.
3. Flash to ESP32.

### 3. Home Assistant & Node-RED
1. Import `node-red/flows.json` into Node-RED.
2. Add `home-assistant/mqtt.yaml` to your Home Assistant `configuration.yaml` includes.

## MQTT Topic Namespace
All topics operate under `labos/v2/`.
- `labos/v2/vision/zones/report` - Published by AI PC, contains zone mapping.
- `labos/v2/automation/mode/set` - Used to set Manual, Monitor, or Auto.
- `labos/v2/relay/+/set` - Relay command topics (Node-RED/HA to ESP32).
- `labos/v2/relay/+/state` - Relay state topics (ESP32 to HA).
- `labos/v2/controller/status` - ESP32 LWT (online/offline).

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

Physical deployment is gated by `docs/validation-checklist.md`. The current known blocker is the RTSP path `rtsp://hari:8554/labcam`, which returns `404 Not Found` until the upstream camera source is restored.
