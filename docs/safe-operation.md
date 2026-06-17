# Safe Operation Guidelines

**Warning**: Lab Automation v2.0 is an active hardware control project. Safety is paramount.

## Safety Rules

1. **Final Safe Mode is Manual**:
   If the system acts unexpectedly, immediately set the mode to `manual` via MQTT or Home Assistant.
   ```bash
   mosquitto_pub -h labos -t lab/automation/mode -r -m manual
   ```

2. **AI Cannot Control Relays**:
   The AI PC is physically and logically blocked from publishing relay commands (`/set`). It only publishes telemetry to `lab/vision/#`.

3. **Auto Requires Supervision**:
   Until the final physical production-readiness sign-off is given, `auto` mode must only be enabled while an operator is present in the lab observing the physical relays and lights.

4. **Monitor Mode for Diagnostics**:
   Use `monitor` mode to view intended states without actually firing physical relays.

5. **Node-RED Is The Only Automation Authority**:
   On the intended v2 design, Home Assistant publishes user mode commands, Node-RED publishes `mode_state`, `priority_state`, and relay `/set`, the AI PC publishes only `lab/vision/#`, and the ESP32 publishes relay `/state`. Legacy helper services on `labos` must not republish `lab/automation/mode` or inject relay `/set` commands.

6. **Stale Vision Does Not Change User Mode**:
   If the user selects `auto`, the system should keep `lab/automation/mode_state = auto` even when RTSP, camera, or AI health becomes stale or unhealthy. In that condition, the controller must fall back to timetable logic instead of forcing Manual mode.

7. **Secrets Management**:
   Never commit `.env` files, passwords, camera URLs with credentials, or Wi-Fi SSIDs to this repository. All credentials should be stored securely on the host machines (e.g., in `~/.config/` or `esp32` local changes).

## Windows AI PC Startup

Use the AI PC startup wrapper from the repository root:

```powershell
.\start_lab_automation.ps1 -DryRun
.\start_lab_automation.ps1
.\start_lab_automation.ps1 -Display
```

Safety behavior of the wrapper:
- verifies `.venv\Scripts\python.exe`, `config\config.yaml`, `config\zones.json`, `models\backcam_yolov8s_improved_v3_hardfp.pt`, and `ai-pc\src\main.py`
- checks MQTT reachability to `labos:1883`
- checks the RTSP stream at `rtsp://hari:8554/labcam`
- attempts to read retained `lab/automation/mode_state` and `lab/vision/heartbeat`
- starts only the AI vision publisher and writes logs under `logs\ai-publisher\`
- `-Display` uses the same publisher and same MQTT safety restrictions, but adds a live OpenCV operator window
- does **not** change the automation mode and does **not** publish any relay/control topics

June 17, 2026 live wrapper validation confirmed:
- headless and display startup use the same `src.main` publisher path
- display mode adds visualization only; it does not loosen MQTT topic restrictions
- live broker captures still showed AI publishing only `lab/vision/#`
- no `lab/control/+/set` messages were observed from the AI publisher during headless or display validation

Use these companion commands as needed:

```powershell
.\status_lab_automation.ps1
.\stop_lab_automation.ps1
```

## Zone and Count Validation Before Auto

Before any physical Auto test, validate the AI display against the live camera:

```powershell
.\start_lab_automation.ps1 -Display
```

Confirm the following in the display window:
- visible people have YOLO boxes
- each person has a bottom-centre foot point
- each foot point lands in the correct camera-perspective zone
- `Current Zone Counts` changes immediately when people are assigned
- `Stable Zone Counts` and `Published Count` update only according to debounce/window logic
- no person is silently dropped unless their foot point is truly outside all polygons

The zone map is defined from the camera image, not the architectural room drawing:
- Zone 1: bottom-left / camera-side
- Zone 2: middle-right / lower-mid
- Zone 3: left/mid visible working area
- Zone 4: top-right
- Zone 5: upper-middle
- Zone 6: top-left

Then verify the broker path from `labos`:

```bash
mosquitto_sub -h localhost -v -F '%I %t %p' -t 'lab/vision/#'
mosquitto_sub -h localhost -v -F '%I %t %p' -t 'lab/control/+/set'
```

AI should publish only `lab/vision/#`. Any `lab/control/+/set` from the AI path is a stop condition.
