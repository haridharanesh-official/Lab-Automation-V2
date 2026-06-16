# Tools and Technology Choices

This document explains why we chose each software tool and hardware component for **Lab Automation v2.0**, along with alternatives we considered and future areas of improvement.

---

## 1. Programming and Scripting Languages

### Python
- **What it does**: Runs the AI computer-vision pipeline and automation helper scripts.
- **Why chosen**: It is the industry standard for AI, machine learning, and rapid scripting.
- **Alternatives**: C++, Go.
- **Why not chosen**: C++ would yield faster speeds but takes much longer to write. Python has excellent libraries (like PyTorch and Ultralytics) out-of-the-box.
- **Future Improvement**: We could compile Python files to optimized bytecode or rewrite critical sections in Rust or C++ to reduce CPU consumption.

### Arduino C++ (`.ino`)
- **What it does**: Controls the hardware pins and network calls on the ESP32 microcontroller.
- **Why chosen**: Highly popular, massive library support for Wi-Fi and MQTT, and lightweight execution on cheap chips.
- **Alternatives**: MicroPython, ESP-IDF (C).
- **Why not chosen**: MicroPython uses more memory and boots slower. ESP-IDF is too complex for basic relay toggling.
- **Future Improvement**: Migrate to ESP-IDF for better security features (TLS, secure boot).

---

## 2. Artificial Intelligence and Computer Vision

### Ultralytics YOLO (v8)
- **What it does**: Detects human shapes in video frames.
- **Why chosen**: "You Only Look Once" (YOLO) is highly accurate and extremely fast on standard graphics cards (GPUs).
- **Alternatives**: TensorFlow Object Detection, OpenCV HOG.
- **Why not chosen**: Older algorithms have high false-positive rates (e.g. mistaking chairs for people). YOLOv8 provides a great balance of speed and precision.

### OpenCV (Open Source Computer Vision Library)
- **What it does**: Grabs video frames from the network stream and draws boxes/text for monitor displays.
- **Why chosen**: Reliable, supports RTSP streaming, and is highly optimized.
- **Alternatives**: GStreamer.
- **Why not chosen**: GStreamer has a steep learning curve and configuration complexity.

### ByteTrack
- **What it does**: Keeps track of detected people across frames using movement association.
- **Why chosen**: Prevents "flicker" in people counts if someone is temporarily blocked by a monitor or pillar.
- **Alternatives**: DeepSORT.
- **Why not chosen**: DeepSORT requires heavy neural-network computation for tracking. ByteTrack is lightweight and fast.

---

## 3. Communication Protocols and Servers

### Mosquitto (MQTT Broker)
- **What it does**: The central "post office" server routing messages between components.
- **Why chosen**: Mosquitto is lightweight, fast, and uses minimal resources.
- **Alternatives**: RabbitMQ, HTTP REST APIs.
- **Why not chosen**: HTTP requires continuous polling which wastes network bandwidth. MQTT is "push-based" and instant.

### Paho MQTT
- **What it does**: The library used by our Python scripts to connect and publish to Mosquitto.
- **Why chosen**: Official, mature, and reliable client library.

### MediaMTX (formerly rtsp-simple-server)
- **What it does**: Re-broadcasts the camera feed as an RTSP stream so the AI PC can read it.
- **Why chosen**: Zero-configuration setup, extremely low latency, and low CPU usage.

---

## 4. Automation and User Interfaces

### Node-RED
- **What it does**: Connects MQTT messages to logic nodes and sets relay states.
- **Why chosen**: Extremely easy to build visual flows, inspect logic paths live, and make safe rules without editing complex backend code.
- **Alternatives**: Custom Python automation scripts.
- **Why not chosen**: Custom scripts are hard to visualize and audit quickly by lab instructors who aren't software developers.

### Home Assistant
- **What it does**: Provides the web dashboard to toggle modes and view system health.
- **Why chosen**: Free, open-source, runs locally, and integrates out-of-the-box with MQTT.
- **Alternatives**: Custom web dashboard.
- **Why not chosen**: Custom dashboards require building, securing, and maintaining a web server. Home Assistant is already secure and ready.

---

## 5. Testing and Data Formats

### Pytest
- **What it does**: Runs automated tests to ensure safety rules aren't broken by new code.
- **Why chosen**: Simple syntax, runs fast, and is standard in Python development.

### YAML and JSON
- **What they do**: Store settings (`.yaml`) and zone geometry coordinate maps (`.json`).
- **Why chosen**: Humans can read and write them easily, and computers can parse them instantly.
