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
3. writes a timestamped log file under:
   - `logs\ai-publisher\YYYYMMDD-HHMMSS.log`
4. stores wrapper PID metadata in:
   - `logs\ai-publisher\ai-publisher.pid.json`

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
- current wrapper PID and log path if running

## Stop Command

```powershell
.\stop_lab_automation.ps1
```

This stops only the wrapper process recorded by `start_lab_automation.ps1`.

The stop script refuses to kill unrelated processes if the PID file points at something that does not look like the AI publisher wrapper.

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
