# Startup and Shutdown

This document covers the safe operator commands for the Windows AI PC side of Lab Automation v2.0.

## Scope

These scripts manage only the AI PC publisher process. They do **not** start or stop:
- Node-RED on `labos`
- Mosquitto on `labos`
- Home Assistant on `labos`
- MediaMTX or the camera bridge on `hari`

Mode authority remains outside the AI PC:
- Home Assistant sends user mode commands on `lab/automation/mode`
- Node-RED confirms controller state on `lab/automation/mode_state`

The AI PC publishes only `lab/vision/#`.

## Start Command

From the repo root:

```powershell
.\start_lab_automation.ps1
```

To start the same AI publisher with a live display window:

```powershell
.\start_lab_automation.ps1 -Display
```

Recommended first pass:

```powershell
.\start_lab_automation.ps1 -DryRun
```

## What Start Checks

Before the AI publisher starts, the script checks:
- Python venv exists at `.venv\Scripts\python.exe`
- runtime config exists at `config\config.yaml`
- zones file exists at `config\zones.json`
- production model exists at `models\backcam_yolov8s_improved_v3_hardfp.pt`
- AI entrypoint exists at `ai-pc\src\main.py`
- MQTT broker is reachable at the configured host/port, currently `labos:1883`
- RTSP stream opens at the configured URL, currently `rtsp://hari:8554/labcam`
- retained topic snapshots if available:
  - `lab/automation/mode_state`
  - `lab/vision/heartbeat`

If any required file or network dependency is missing, the script stops with a clear error and does not start the publisher.

## Start Behavior

When checks pass, the script:
1. sets `PYTHONPATH=ai-pc`
2. starts the existing publisher:
   - `.venv\Scripts\python.exe -m src.main --config config/config.yaml`
   - or `.venv\Scripts\python.exe -m src.main --config config/config.yaml --display` when `-Display` is used
3. writes a timestamped log file under:
   - `logs\ai-publisher\YYYYMMDD-HHMMSS.log`
4. stores wrapper PID metadata in:
   - `logs\ai-publisher\ai-publisher.pid.json`

In display mode the publisher opens a live OpenCV window that shows:
- current camera frame
- YOLO person boxes
- confidence values
- track IDs when available from the tracker
- zone polygons
- bottom-centre assignment point for each detected person
- assigned zone label or `OUT` marker for each person foot point
- current per-zone counts
- rolling stable/window zone counts
- debounced published people count
- window sample count and seconds until report
- FPS
- inference latency
- source health

Close the live session with `q` in the OpenCV window or by stopping the launched publisher process.

The wrapper does **not**:
- switch the system to `auto`
- publish relay commands
- touch `lab/control/#`
- change Home Assistant or Node-RED mode state

## Status Command

```powershell
.\status_lab_automation.ps1
```

This reports:
- configured camera URL
- whether the camera host/port is reachable
- whether MQTT is reachable
- latest retained `lab/automation/mode_state` if available
- latest retained vision heartbeat age if available
- whether the AI publisher process appears to be running
- how many matching `src.main --config config/config.yaml` publisher processes are present
- whether the current publisher was started in display mode
- current wrapper PID and log path if running

## Stop Command

```powershell
.\stop_lab_automation.ps1
```

This stops only the AI publisher path started from this repo. It stops:
- the wrapper process recorded by `start_lab_automation.ps1`
- child Python publisher processes spawned by that wrapper
- matching orphaned `src.main --config config/config.yaml` publisher processes from this repo if the PID file is stale or missing

The stop script refuses to kill unrelated processes if the PID file points at something that does not look like the AI publisher wrapper.

## June 17, 2026 Validation Result

Live startup/shutdown validation on the Windows AI PC confirmed:
- `.\start_lab_automation.ps1 -DryRun` passes against the real broker and RTSP stream
- `.\start_lab_automation.ps1 -DryRun -Display` passes against the real broker and RTSP stream
- `.\start_lab_automation.ps1` starts the headless publisher and writes a timestamped log
- `.\start_lab_automation.ps1 -Display` starts the same publisher in display mode and records `display=true` in PID metadata
- `.\status_lab_automation.ps1` reports the running PID, log path, and display flag
- `.\stop_lab_automation.ps1` stops either headless or display mode cleanly
- Follow-up live debugging found that stopping only the wrapper could leave Python child publishers alive, causing duplicate `lab/vision/people_count` streams. The scripts now detect matching publisher processes before start, report the matching process count in status, and stop matching orphaned child publishers.

Root cause of the reported display bug:
- older PID metadata files did not contain the `display` field
- the scripts now check whether that property exists before reading it

## Logs

Publisher logs are stored here:

```text
logs/ai-publisher/
```

Each run gets a timestamped log file. The current wrapper PID and active log path are tracked in `ai-publisher.pid.json`.

## Safety Notes

- Keep final safe mode as `manual` unless a supervised validation explicitly requires another mode.
- The AI publisher code itself rejects unsafe topics outside `lab/vision/#`.
- Use `.\status_lab_automation.ps1` before assuming the publisher is down; the system may already be running.
