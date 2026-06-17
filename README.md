# Lab Automation v2.0

## Project Overview
An AI-driven, multi-zone room automation system using YOLOv8, Home Assistant, Node-RED, and ESP32. It is designed to track occupancy and automate laboratory lighting/fans based on people count, with safety as the primary concern.

## Current Status
- **Software validation**: Complete
- **Monitor-mode empty-lab validation**: Passed for ~11 minutes (0 false positives, 0 relay `/set` commands)
- **Hardware deployment**: Pending
- **Production-ready**: **NO**. Not physically production-ready until occupied-scene supervised relay validation passes.

## Architecture
`Camera -> AI PC -> lab/vision/# -> Mosquitto -> Node-RED -> lab/control/relayX/set -> ESP32`

## Hardware and Software Stack
- **AI PC**: Python 3.11, PyTorch, Ultralytics YOLOv8
- **Camera Bridge**: MediaMTX (RTSP server) on `hari`
- **Broker**: Eclipse Mosquitto
- **Controller**: Node-RED on `labos`
- **Dashboard**: Home Assistant
- **Firmware**: Custom ESP32 C++ with 10 active-LOW relays

## Folder Structure
- `ai-pc/`: YOLOv8 vision logic, zone mapping, and safe simulator
- `node-red/flows.json`: Importable priority-safety automation controller flow
- `esp32/`: Ten-relay controller firmware (original design uses `labos/v2/`)
- `home-assistant/mqtt.yaml`: MQTT entities
- `config/`: Secret-free example configuration and zone polygons
- `tests/`: Software safety verification
- `docs/`: Architecture, topics, validation, troubleshooting, readiness, status reports

## Beginner-Friendly Documentation Guides
If you are new to the project, start with these guides:
- [Project Explained for Beginners](file:///c:/Users/prith/Downloads/Lab%20Automation%20v2.0/docs/project-explained-for-beginners.md): What the project does, how components connect, and basic safety rules in plain English.
- [File-by-File Guide](file:///c:/Users/prith/Downloads/Lab%20Automation%20v2.0/docs/file-by-file-guide.md): A complete explanation of every folder, script, config, and file extension in the repository.
- [Logic Explained](file:///c:/Users/prith/Downloads/Lab%20Automation%20v2.0/docs/logic-explained.md): A detailed look at the AI detection flow, priority rules, and no-flicker logic.
- [Tools and Technology Choices](file:///c:/Users/prith/Downloads/Lab%20Automation%20v2.0/docs/tools-and-technology-choices.md): Why we chose YOLOv8, MQTT, Node-RED, ESP32, etc., and alternative options.
- [Improvement Roadmap](file:///c:/Users/prith/Downloads/Lab%20Automation%20v2.0/docs/improvement-roadmap.md): Planned security updates, testing tasks, and diagnostics.

## MQTT Topic Contract
The current deployed `labos` runtime uses the `lab/...` namespace. The AI publisher is restricted to the `lab/vision/#` namespace.
- `lab/vision/people_count`: Debounced people-count JSON published by AI for Home Assistant and Node-RED automation
- `lab/vision/raw_people_count`: Raw current detection JSON published by AI for diagnostics only
- `lab/vision/status`, `lab/vision/source_status`, `lab/vision/heartbeat`: Telemetry from AI
- `lab/automation/mode`: Mode selection (`manual`, `monitor`, `auto`)
- `lab/automation/mode_state`: Confirmed controller mode state for dashboards and validation
- `lab/control/relayX/set`: Relay commands (Published **ONLY** by Node-RED)
- `labos/v2/...`: Original hardware spec/namespace (for ESP32 references)

## Camera Bridge Summary
The RTSP bridge (`rtsp://hari:8554/labcam`) has been hardened with a dedicated systemd service and a health check timer. It currently runs continuously and provides a 1280x720 H.265 stream for the AI PC.

## AI Publisher Behavior
The AI publisher **must never** publish relay commands. It is blocked from `lab/control/#` or any topic ending in `/set`. It publishes vision reports only under `lab/vision/#`.

`lab/vision/people_count` is intentionally debounced for HA and Node-RED. Brief missed detections do not immediately publish zero, and the last known good count is preserved during camera/AI uncertainty. `lab/vision/raw_people_count` may move faster and is useful only for diagnostics.

## Zone Calibration
`config/zones.json` is calibrated in live 1280x720 camera-image coordinates, not from the architectural top-down room diagram. Current provisional camera-perspective numbering is:
- Zone 1: bottom-left / camera-side
- Zone 2: middle-right / lower-mid
- Zone 3: left/mid visible working area
- Zone 4: top-right
- Zone 5: upper-middle
- Zone 6: top-left

The current polygons are an improved initial calibration only. Do not trust physical Auto mode until live occupied-scene zone assignment is verified with people standing, seated, moving, and near boundaries.

To validate zones safely, run the live display:

```powershell
.\start_lab_automation.ps1 -Display
```

The display must show YOLO boxes, bottom-centre foot points, assigned zone labels, current zone counts, stable zone counts, and the debounced published count. If a person is visible but their foot point is marked `OUT`, update the polygon from the camera frame before using Auto.

For controlled one-zone-at-a-time validation, use:

```powershell
.\.venv\Scripts\python.exe ai-pc\tools\live_zone_walk_test.py
```

In the live window, press `1`-`6` when the supervised test person is standing in that expected zone, press `s` to save a snapshot, and press `q` to quit. Logs and screenshots are saved under `monitor-results\zone-walk\`.

To test a single pixel foot point without opening the camera:

```powershell
.\.venv\Scripts\python.exe ai-pc\tools\live_zone_walk_test.py --point 320,650
```

## Node-RED Safety Logic
Node-RED enforces a strict priority order:
1. **Manual Override**: Highest priority. Overlays manual states over automation.
2. **Timetable Fallback**: Triggers if vision is stale or unhealthy. Applies a safe state during class hours and delays OFF transitions.
3. **Healthy Automation**: Triggers only when the camera and AI are healthy. Emits no-flicker state changes based on people count.

## Operating Modes
- `manual`: Safest mode. Node-RED ignores AI count and never emits relay `/set`. This is the final safe mode.
- `monitor`: Diagnostic mode. Calculates intended state and logs warnings, but sends zero relay commands.
- `auto`: Active automation. Requires supervision until fully validated.

## Setup / Run Commands

### 1. Python Environment (AI PC)
```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -e .
pytest tests/
```

### 2. Node-RED & Home Assistant
1. Import `node-red/flows.json` into Node-RED.
2. Ensure Node-RED mode defaults to `manual`.
3. Add `home-assistant/mqtt.yaml` to Home Assistant `configuration.yaml` includes.

### 3. Run Vision / Monitor
```bash
# Windows PowerShell helper
.\run_monitor.ps1
```

Equivalent direct command:

```bash
set PYTHONPATH=ai-pc
.\.venv\Scripts\python.exe -m src.main --config config/config.yaml
```

Preferred operator wrapper on the Windows AI PC:

```powershell
.\start_lab_automation.ps1 -DryRun
.\start_lab_automation.ps1
.\start_lab_automation.ps1 -Display
.\status_lab_automation.ps1
.\stop_lab_automation.ps1
```

What these scripts do:
- `start_lab_automation.ps1`: verifies the venv, config, zones, model, RTSP stream, MQTT broker, and live retained topics before starting the AI publisher with log capture. Use `-Display` to launch the same publisher with a live OpenCV overlay window.
- `stop_lab_automation.ps1`: stops the AI publisher wrapper and matching Python child/orphan publisher processes from this repo.
- `status_lab_automation.ps1`: shows camera reachability, MQTT reachability, latest `mode_state`, heartbeat age, whether the AI publisher appears to be running, matching publisher process count, and whether it was started in display mode.

June 17, 2026 startup validation notes:
- headless startup and shutdown were validated against the live `labos` broker and `hari` RTSP stream
- display startup was validated against the live broker/stream and now records `display=true` in PID metadata cleanly
- if an old `logs/ai-publisher/ai-publisher.pid.json` file exists from before display mode was added, the scripts now tolerate the missing `display` property instead of crashing
- follow-up MQTT debugging found orphaned Python publisher children can create duplicate AI publisher streams if only the wrapper process is stopped; the scripts now detect duplicates and stop matching repo publisher children/orphans

### 4. Other Existing Operator Scripts

- Setup Windows environment:
  - `.\setup_windows.ps1`
- Run safe simulator:
  - `.\simulate_reports.ps1`
- Open zone editor:
  - `.\calibrate_zones.ps1 -Image <path-to-image>`
- Live RTSP monitor window:
  - `.\.venv\Scripts\python.exe tools\live_stream_monitor.py`
- Live validation overlay:
  - `.\.venv\Scripts\python.exe tools\live_model_validation.py --source rtsp://hari:8554/labcam --model models/backcam_yolov8s_improved_v3_hardfp.pt --conf 0.35 --image-size 1280 --device 0 --tracker bytetrack.yaml --zones config/zones.json --duration 600 --display --output-dir monitor-results/live-validation`

### 5. Current Startup Reality

- `hari` has user services for `mediamtx.service`, `labos-camera-bridge.service`, and `labcam-healthcheck.timer`.
- `labos` has system services for Node-RED-adjacent helpers, event logging, mock relay behavior, and health/status monitoring.
- The AI PC currently has helper scripts, but no repo-tracked Windows service, Scheduled Task, or startup script that automatically launches the live MQTT publisher on boot/login.
- The new master wrapper scripts provide a safe manual startup path, but they still do not install a Windows auto-start service or Scheduled Task.

## Validation History
- AI publisher accepts only safe topics.
- Monitor-mode validation passed with 23 software tests.
- Camera bridge hardened after upstream connectivity issues.
- Deployed Node-RED flow correctly processes `lab/vision/people_count`.
- Empty-lab stability test: 11 minutes in Monitor mode yielded repeated `stable_count = 0` and no relay changes.
- June 17 count-path fix: live display now separates current zone counts from stable/window counts, draws bottom-centre assignment points, and publishes debounced `lab/vision/people_count` separately from raw `lab/vision/raw_people_count`.
- June 17 zone correction: zone polygons were changed to live camera-perspective numbering; the old top-down room diagram is not directly usable for image polygons.
- June 17 end-to-end validation: display mode opened `rtsp://hari:8554/labcam`; `labos` received fresh `lab/vision/status`, `lab/vision/source_status`, `lab/vision/heartbeat`, and debounced `lab/vision/people_count`; Node-RED processed the count in Manual and Monitor; Monitor emitted 0 relay `/set` commands; a short Auto logic check confirmed `mode_state=auto` and returned to `manual`.

## Next Validation Step
1. Occupied-scene Monitor validation when a person is visible.
2. Supervised Auto validation.
3. Physical light/fan mapping confirmation.

## Remaining Blockers
- Supervised occupied-scene Auto tests remain incomplete.
- Physical relay behavior and mapping must be validated.
- Zone calibration needs supervised confirmation.

## Safety Warnings
- **DO NOT** enable physical `auto` mode without supervision until full validation passes.
- Final safe mode is always `manual`.
- **NEVER** commit Wi-Fi passwords, camera credentials, or MQTT secrets.
