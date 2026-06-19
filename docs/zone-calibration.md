# Zone Calibration

Lab Automation v2.0 uses a custom OpenCV zone editor because the final zone
polygons must be clicked directly in the live camera frame. Architectural
top-down room diagrams are not accurate enough for camera-perspective bottom
center assignment.

This workflow is calibration-only. It must not deploy Node-RED, switch
automation modes, publish relay MQTT topics, or touch relay control.

## Current Safety Boundary

- Current live Auto authority is still people-count based.
- `zone-count` is calibration and Monitor-safe only.
- Zone mapping must be validated in Monitor mode before any future Auto logic
  is allowed to use zone counts.
- The live hardware is still 8 relays. Relay 1 and relay 5 are spares and are
  unrelated to zone calibration.

## Capture A Frame

Use an existing image or capture one frame from the lab RTSP stream:

```powershell
.\.venv\Scripts\python.exe tools\capture_lab_frame.py --rtsp rtsp://hari:8554/labcam
```

The command prints the saved image path. It only reads the camera stream and
writes an image file.

## Open The Editor

```powershell
.\.venv\Scripts\python.exe tools\zone_editor.py --image monitor-results\zone-calibration\labcam-YYYYMMDD-HHMMSS.jpg
```

Or capture one RTSP frame directly when opening:

```powershell
.\.venv\Scripts\python.exe tools\zone_editor.py --rtsp rtsp://hari:8554/labcam
```

## Editor Controls

- `1` to `6`: select the active zone.
- Left click: add a point to the active zone.
- Right click or `U`: undo the last point in the active zone.
- `C`: clear the active zone.
- `R`: reset all zones after typing `RESET` in the console.
- `T`: toggle point-test mode.
- `S`: save `config/zones.json` after validation.
- `L`: reload existing `config/zones.json`.
- `B`: create a manual backup of `config/zones.json`.
- `H`: show or hide help overlay.
- `Q` or `Esc`: quit.

## Point Testing

Runtime assignment uses the bottom-center point of each detected person box.
In point-test mode, click where a person's feet touch the floor in the image.
The editor reports:

- `UNKNOWN` when the point is in no zone.
- A zone number when the point is uniquely assigned.
- An overlap warning when the point is inside multiple zones. The deterministic
  result is the lowest zone ID.

## Validation Rules

Saving is blocked when:

- there are not exactly six zones;
- any zone has fewer than three points;
- zone IDs are not exactly `1` through `6`;
- any point is outside the image bounds;
- the JSON is invalid or cannot be normalized.

Saving is allowed with warnings when:

- zones overlap;
- a large part of the image is unmapped.

Before overwriting `config/zones.json`, the editor creates a timestamped backup
beside it.

## Validate Without GUI

```powershell
.\.venv\Scripts\python.exe tools\validate_zones.py --zones config\zones.json
```

To test a bottom-center point:

```powershell
.\.venv\Scripts\python.exe tools\validate_zones.py --zones config\zones.json --point 260 650
```

## Run Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_zones.py
.\.venv\Scripts\python.exe -m pytest
```

If the OpenCV GUI cannot run in a remote or headless session, run the non-GUI
validation and tests above, then run `tools\zone_editor.py` directly on the
Windows AI PC desktop.
