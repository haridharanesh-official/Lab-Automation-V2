# Improvement Roadmap

This roadmap outlines the future features, validations, and security improvements planned for **Lab Automation v2.0**.

---

## 1. Short-Term: Deployed Validation (Blockers to Production)

These tasks must be completed before the system can be considered production-ready.

- [ ] **Occupied-Scene Monitor Validation**:
  - Run the AI PC and Node-RED in `monitor` mode while operators are in the lab.
  - Verify that the AI correctly detects people, counts them, and maps them to zones.
  - Verify that Node-RED's calculated `intended_state` matches expected lights/fans without sending real commands.
- [ ] **Physical Relay Mapping Validation**:
  - Flash the ESP32 with the final pin assignments.
  - Turn each relay on/off manually using Home Assistant.
  - Verify that Relay 1 actually maps to the intended Light/Fan 1, Relay 2 maps to Light/Fan 2, and so on.
- [ ] **Supervised Auto-Mode Validation**:
  - Turn on `auto` mode under strict supervision.
  - Verify that lights and fans switch ON and OFF smoothly when people enter and leave.
  - Check for flicker or unexpected state changes.

---

## 2. Medium-Term: Security and Reliability

- [ ] **MQTT Authentication and ACLs**:
  - Currently, MQTT has username/password set to empty. We need to enable authentication.
  - Implement Access Control Lists (ACLs) to ensure the AI PC can **only** publish to `lab/vision/#`, and only Node-RED can publish to `lab/control/#`.
- [ ] **Camera Freeze Detector**:
  - Sometimes a camera network stream hangs but continues returning the last captured frame (a "frozen frame").
  - Add logic to the AI PC to check if pixel values are 100% identical over multiple seconds, indicating a frozen stream, and trigger a safety shutdown or alarm.
- [ ] **Relay Mismatch Alerts**:
  - If Node-RED sends a command (e.g. Relay 2 to `ON`) but the ESP32 reports that the relay state is still `OFF` after 5 seconds, publish a warning.
- [ ] **Backup and Restore Scripts**:
  - Create a single script to backup Node-RED flows, ESP32 code, and configuration settings to a local drive.

---

## 3. Long-Term: Diagnostics and UI

- [ ] **Dashboard / Command Center**:
  - Create a dedicated local web dashboard displaying active camera streams, zone polygon coordinates, occupancy stats, and system logs.
- [ ] **Energy Usage Reports**:
  - Calculate the daily energy saved by comparing actual automated runtime against a simulated traditional "always-on" timetable.
- [ ] **Home Assistant UI Improvements**:
  - Design a map representation of the lab showing live colored indicators for each zone (e.g. green for empty, red for occupied).
- [ ] **Local AI Assistant**:
  - Integrate a local Large Language Model (LLM) that can read the MQTT logs and explain anomalies in simple English (e.g., "The lights stayed on at 9 PM because a student was detected in Zone 3").
- [ ] **Timeline History Logs**:
  - Keep a chronological timeline of mode changes, overrides, and camera dropouts in a CSV or database for offline performance audits.
