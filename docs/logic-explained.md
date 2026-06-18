# Logic Explained

This document explains the step-by-step logic used in **Lab Automation v2.0**. It describes how the AI PC detects people, how Node-RED makes decisions, and how safety overrides are managed.

---

## 1. The AI Detection and Publishing Flow

The AI PC runs a repeating loop that processes live camera footage:

```
[Grab Frame] 
      │
      ▼
[Run YOLOv8 Model] ──(Find Bounding Boxes of People)──► [Filter by Confidence (>0.35)]
                                                                  │
                                                                  ▼
[Calculate Feet Coordinate (X, Y)] ◄─────────────── [ByteTrack Tracking Model]
      │
      ▼
[Zone Assignment Check] ──(Is foot-point inside zone polygon?)
      │
      ▼
[MQTT Publish Telemetry] ──(Send counts & status to lab/vision/#)
```

### Key Steps:
1. **Model Filtering**: The YOLOv8 model finds all objects in the camera frame. It keeps only objects categorized as a "person" with a confidence score above `0.35` (35%).
2. **ByteTrack**: Tracking helps identify individual people across consecutive video frames, reducing duplicate counts if someone moves slightly.
3. **Feet Location Mapping**: To map a person's location, the code calculates the **bottom-middle point** of their bounding box (their feet). This is much more accurate than using their head or chest, which changes depending on posture.
4. **Zone Assignment**: The system checks if the foot-point coordinates fall inside any of the six user-defined zone polygons (`zones.json`).
5. **Safe Publishing**: Telemetry reports are sent to the MQTT broker. If any errors occur, the script drops MQTT connections rather than risking sending wrong or stale data.

---

## 2. Node-RED Decision Flow (The Priority Safety Controller)

When Node-RED receives messages from the MQTT broker, it processes them using a **strict priority hierarchy**. Higher-priority rules override lower ones.

```
       [Start: Mode is AUTO]
                 │
                 ▼
      [Rule 1: Manual Override?] ────► (Yes) ──► Apply manual states
                 │ (No)
                 ▼
      [Rule 2: Vision Stale/Error?] ──► (Yes) ──► Trigger Timetable Fallback State
                 │ (No)
                 ▼
      [Rule 3: Occupancy Rules?] ────► (Yes) ──► Calculate target state from count
                 │
                 ▼
      [Command Deduplication] ────► Compare with physical relay feedback
                 │
                 ▼
      [Send lab/control/relayX/set]
```

### Priority 1: Manual Override (Highest Priority)
- **What it is**: If a user toggles a switch manually on the wall or in Home Assistant, that choice overrides the automation.
- **Why**: Human control must always have the final say in an emergency or special event.
- **How it works**: Node-RED listens to `/state` topics from the ESP32. If a state changes without an automation command, or if manual mode is active, it flags that relay as "overridden". It stays locked in that state until the manual override is cleared (on `lab/automation/manual_override/clear`).

### Priority 2: Timetable Fallback (Safety Net)
- **What it is**: Triggered if the AI PC heartbeats stop or if `vision_health` is marked `stale` (no update in over 10 seconds).
- **Why**: We must not assume the lab is empty just because the camera crashed.
- **How it works**:
  - **Inside Class Hours** (`08:30-12:30` and `13:00-16:30`): Turn on/keep on the baseline relays (`2, 3, 4, 6, 7, 8`) to ensure students can work safely.
  - **Outside Class Hours**: Preserve the last known state.

### Priority 3: Occupancy Rules (Default Automation)
- **What it is**: Runs only when the AI PC telemetry is healthy.
- **Rules**:
  - `1 person` => Turn on Relays `2, 7` (Zone 1 / baseline)
  - `2-3 people` => Turn on Relays `2, 3, 6, 7`
  - `4+ people` => Turn on Relays `2, 3, 4, 6, 7, 8`

---

## 3. No-Flicker & Safe Shutdown Logic

Rapidly switching lights or fans ON and OFF (flickering) can damage electrical components and annoy lab users. We prevent this using two mechanisms:

### A. Two-Empty-Report Guard
When the AI PC reports `people_count: 0`, the lights do not turn off immediately. Node-RED requires **two consecutive empty reports** (separated by the reporting interval, e.g., 60 seconds) before initiating a shutdown sequence.

### B. Command Deduplication
Before Node-RED publishes a `lab/control/relayX/set` message, it checks the current confirmed `/state` of the relay. If the relay is already `ON`, it does not send another `ON` command. This minimizes network traffic and prevents relay cycling.

---

## 4. Why Immediate All-OFF is Unsafe

If a network glitch causes the AI PC to temporarily report `0` people when there are actually 10, turning off all lights immediately would leave everyone in the dark. 

By enforcing **stale camera handling** (freezing state on failure), **continuous empty-room delay**, and **Auto-only correction**, glitches preserve the current relay state rather than making stale data force loads ON or OFF.
