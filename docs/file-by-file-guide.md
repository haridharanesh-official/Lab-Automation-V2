# File-by-File Guide

This guide explains the folder structure, file extensions, and every important file in the **Lab Automation v2.0** repository. It helps you understand what each file contains, why it exists, how it connects to other parts of the project, and whether you should edit it.

---

## 1. File Extensions Used in This Project

Before looking at the files, here is a quick guide to what the file extensions mean:
- **`.md` (Markdown)**: Simple text documents containing headings, lists, and tables (like this guide).
- **`.py` (Python)**: Code scripts containing the Artificial Intelligence and telemetry logic.
- **`.json` (JSON)**: Data files that store lists or structures (like zone coordinates or Node-RED flows).
- **`.yaml` or `.yml` (YAML)**: Configuration files used to set options like confidence levels, device ports, or Home Assistant setups.
- **`.ps1` (PowerShell Script)**: Automation scripts for Windows to set up or run commands.
- **`.ino` (Arduino Sketch)**: Firmware source code written in C++ for the ESP32 microcontroller.

---

## 2. Root Folder Structure Overview

Here are the primary folders and files in the root of the project:

```
[Lab Automation v2.0]
 ├── ai-pc/                      # AI PC logic (Python)
 ├── config/                     # Configuration files (YAML, JSON)
 ├── docs/                       # Project documentation (Markdown)
 ├── esp32/                      # Microcontroller firmware (Arduino C++)
 ├── home-assistant/             # Dashboard integrations (YAML)
 ├── node-red/                   # Control flows (JSON)
 ├── tests/                      # Testing script suite (Python)
 ├── README.md                   # Project landing page
 ├── pyproject.toml              # Python package metadata
 └── *.ps1                       # Helper scripts for Windows execution
```

---

## 3. Detailed File and Folder Guide

### A. Root Level Configuration & Automation Scripts

#### `README.md`
- **Path**: `/README.md` (Markdown)
- **What it is**: The main landing page of the repository.
- **Purpose**: Gives an immediate overview, architecture map, setup commands, and links to all other documents.
- **Connects to**: Everything.
- **Should you edit it?**: Only when adding new features or changing the global layout.

#### PowerShell Scripts (`setup_windows.ps1`, `calibrate_zones.ps1`, `run_monitor.ps1`)
- **Path**: `/*.ps1` (PowerShell Script)
- **What they are**: Automated script commands for Windows.
- **Purpose**:
  - `setup_windows.ps1` installs Python requirements and configures the virtual environment automatically.
  - `calibrate_zones.ps1` starts a utility to let you align zones on the camera feed.
  - `run_monitor.ps1` runs the AI code in safe Monitor mode.
- **Should you edit them?**: Usually no, unless your path setup or Python command names change.

---

### B. The `ai-pc/` Folder (Artificial Intelligence & Vision)

This folder contains Python scripts that capture the video stream, run the YOLOv8 model, count people, and publish the telemetry over MQTT.

#### `ai-pc/src/main.py`
- **Path**: `/ai-pc/src/main.py` (Python code)
- **Purpose**: The main starting point of the AI service. It coordinates capturing video frames, calling the detector, assigning people to zones, and calling the publisher.
- **Should you edit it?**: Only if you are changing how video frames are processed.

#### `ai-pc/src/automation.py`
- **Path**: `/ai-pc/src/automation.py` (Python code)
- **Purpose**: Evaluates rules for mode transitions, checks system health, and guards against invalid state changes.
- **Should you edit it?**: No. It is validated by automated tests.

#### `ai-pc/src/mqtt_publisher.py`
- **Path**: `/ai-pc/src/mqtt_publisher.py` (Python code)
- **Purpose**: Connects to the MQTT broker and safely sends messages to the `lab/vision/#` topics. Implements strict guards preventing any control or relay `/set` messages.
- **Should you edit it?**: Only if adding new telemetry indicators.

#### `ai-pc/src/zones.py`
- **Path**: `/ai-pc/src/zones.py` (Python code)
- **Purpose**: Handles mathematical geometry to determine if a person's foot-point falls inside the coordinates of a specific zone.
- **Should you edit it?**: No, unless you are changing the number of zones.

---

### C. The `config/` Folder (Configuration)

#### `config/config.yaml`
- **Path**: `/config/config.yaml` (YAML configuration)
- **Purpose**: Stores parameters like the camera stream URL, YOLOv8 model paths, confidence thresholds, and MQTT broker IP.
- **Connects to**: Read by `ai-pc/src/main.py`.
- **Should you edit it?**: **YES**. This is where you configure the system for your local network. **IMPORTANT**: Keep your local passwords out of version control by keeping this file local.

#### `config/zones.json`
- **Path**: `/config/zones.json` (JSON data)
- **Purpose**: Contains the raw X and Y coordinates mapping out the polygons for Zones 1-6 in the lab.
- **Connects to**: Read by `ai-pc/src/zones.py` to evaluate occupancy.
- **Should you edit it?**: Yes, using the calibration tool when setting up the camera.

---

### D. The `node-red/` Folder (Decision Brain)

#### `node-red/flows.json`
- **Path**: `/node-red/flows.json` (JSON export)
- **Purpose**: Contains the visual program logic for Node-RED.
- **What it does**: Implements the manual override, class timetable rules, people-count thresholds, and sends the actual `lab/control/relayX/set` messages to the ESP32.
- **Should you edit it?**: You should import it into the Node-RED visual editor. If you modify it visually, export it back to this file to update the repository.

---

### E. The `esp32/` Folder (Relay Hardware Controller)

#### `esp32/lab_automation_v2/lab_automation_v2.ino`
- **Path**: `/esp32/lab_automation_v2/lab_automation_v2.ino` (Arduino C++)
- **Purpose**: Firmware compiled and flashed onto the physical ESP32 chip.
- **What it does**: Sets up pins as output switches (relays), connects to Wi-Fi, connects to MQTT, publishes LWT (online/offline status), listens for `/set` messages, and reports confirmed `/state` back.
- **Should you edit it?**: **YES**. Fill in your Wi-Fi SSID and password local to your IDE before flashing, but do not commit your credentials to Git.

---

### F. The `home-assistant/` Folder (User Interface)

#### `home-assistant/mqtt.yaml`
- **Path**: `/home-assistant/mqtt.yaml` (YAML configuration)
- **Purpose**: Tells Home Assistant how to build dashboard controls (buttons, sensors, indicators) mapping to our MQTT topics.
- **Should you edit it?**: Yes, if you want to add new switches or sensor dials to your Home Assistant dashboard.

---

### G. The `tests/` Folder (Automated Verification)

- **Path**: `/tests/` (Python code)
- **Purpose**: Programmatic verification tests. They run mock simulations of the AI and publisher to prove they cannot publish forbidden MQTT topics and that safety window behaviors work correctly.
- **Should you edit it?**: Only when writing new test cases.
