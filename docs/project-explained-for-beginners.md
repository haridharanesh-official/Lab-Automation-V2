# Project Explained for Beginners

Welcome to the beginner-friendly guide to **Lab Automation v2.0**! This document explains what this project is, how it works, and the core rules we use to keep everything safe, even if you have no background in computer programming.

---

## 1. What Problem Does This Solve?

Imagine a large university laboratory with multiple rows, tables, or zones. In many labs, people forget to turn off lights or fans when they leave, wasting energy. Alternatively, they might turn them off while someone is still working in a corner, causing a safety hazard.

**Lab Automation v2.0** uses smart cameras and Artificial Intelligence (AI) to look at the room, count the number of people in different zones, and automatically control the lights and fans so that:
- Lights and fans turn on when people are in a zone.
- Lights and fans turn off when a zone is empty.
- Critical safety defaults protect users from sudden darkness or malfunctioning equipment.

---

## 2. How the Components Work Together

This system is built from several pieces of hardware and software working like a team. Here is how they communicate:

```
[Camera] ---> [AI PC] ---> [MQTT Broker] ---> [Node-RED] ---> [ESP32 Relay Controller] ---> [Lights/Fans]
```

1. **The Camera**: A security camera mounted in the lab shoots live video of the room. It sends this video stream over the network (using a link like `rtsp://hari:8554/labcam`).
2. **The AI PC**: A computer running an Artificial Intelligence model (YOLOv8) watches the video. It identifies people in the room and figures out which specific "zones" (tables or rows) they are standing or sitting in.
3. **The MQTT Broker (Post Office)**: MQTT is a simple communication protocol that acts like a post office. When the AI PC counts the people, it writes the numbers on "postcards" (called **MQTT Messages**) and sends them to the Broker (hosted on a machine named `labos`). The Broker delivers these postcards to anyone who is listening.
   - **Active Topics**: The live system uses `lab/...` topics, such as `lab/vision/#` for vision telemetry, `lab/automation/#` for mode control, and `lab/control/#` for relay commands.
   - **Legacy Specs**: The name `labos/v2/#` is reserved exclusively as historical/spec context for ESP32 firmware mapping and compatibility.
4. **Node-RED (The Brain)**: Node-RED is a visual automation program running on `labos`. It receives the people-count postcards, checks the time of day, applies safety checks, and makes the actual decisions (e.g., "It is 3:00 PM, Zone 1 is empty, let's turn off Relay 2").
5. **ESP32 Relay Controller**: A small, inexpensive microcontroller (like a mini-computer) connected to the lab's Wi-Fi. It listens for commands from Node-RED. When Node-RED says "turn off Relay 2", the ESP32 physically flips an electrical switch (called a **Relay**) to cut the power to that light or fan.
6. **Lights and Fans**: The actual physical appliances in the lab.

---

## 3. What Happens in Each Mode?

To prevent accidents, the system can run in three different operating modes. You can change this mode using a dashboard.

| Mode | What the AI Does | What Node-RED Does | What the Lights/Fans Do |
| :--- | :--- | :--- | :--- |
| **Manual** | Watches the room and publishes counts. | Ignores the AI counts. Emits zero control commands. | Stay exactly as they are. Users can toggle them by hand or via Home Assistant. **(This is the final safe mode)** |
| **Monitor** | Watches the room and publishes counts. | Calculates what the lights *should* do, but sends zero commands to the relays. | Stay exactly as they are. This is used to test the system safely without flipping physical switches. |
| **Auto** | Watches the room and publishes counts. | Actively sends commands to turn lights/fans ON or OFF based on occupancy. | Automatically switch based on people count. **Requires active human supervision!** |

---

## 4. What Happens During Camera or AI Failure?

If the camera wire is unplugged, the stream freezes, or the AI computer crashes, we must not plunge the lab into sudden darkness. 

If the system stops receiving fresh heartbeats from the AI:
- **No Sudden Shutdown**: The system does **not** assume the room is empty. 
- **State Preservation**: The current states of the relays are locked (preserved) as they are.
- **Timetable Fallback**: The system falls back to a time-of-day schedule. If it is during normal class hours, the lights are turned on or kept on. If it is late at night, the system waits for a long delay before turning lights off, ensuring nobody is left in the dark.

---

## 5. Core Safety Rules

To make sure the system is safe, we enforce three strict rules:

### A. Local-First
All code, models, and communications run inside the lab's local network. We do not use "the cloud" or external internet servers. If the internet goes down, the lab automation still works safely.

### B. "AI Publishes Only Telemetry"
The AI is smart at finding people, but it is not allowed to make decisions. The AI PC is blocked from publishing relay commands directly. It only publishes telemetry (like `people_count: 3`). Only **Node-RED** is allowed to publish relay `/set` commands.

### C. Final Safe Mode is Manual
The system defaults to `manual` mode on boot. In case of any emergency or unexpected behavior, switching to `manual` stops all automated relay switches immediately.

---

## 6. Current Status: Is it Ready?

- **Software**: Checked and fully working.
- **Empty-Lab Live Validation**: Passed. The system watched an empty lab for 11 minutes and made zero mistakes.
- **Production-Ready**: **NO**. The system is NOT production-ready yet. We must first verify that it behaves correctly when real people walk in (occupied-scene validation) and ensure that Relay 1 actually controls Light 1, Relay 2 controls Light 2, etc. (physical mapping validation).
