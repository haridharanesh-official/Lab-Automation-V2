# Live Monitor Validation

Date: June 16, 2026

## Safe Runtime Configuration

- Mode: Monitor
- Model: `models/backcam_yolov8s_improved_v3_hardfp.pt`
- People-only class: `0`
- Confidence: `0.35`
- Image size: `1280`
- Device: CUDA `0`
- Tracker: ByteTrack
- MQTT: disabled in local ignored runtime configuration

## RTSP Verification

Previously documented sources were checked read-only without changing camera settings:

- LAN source `rtsp://172.16.3.31:8554/labcam`: timed out after approximately 30 seconds; zero frames decoded.
- Tailscale fallback `rtsp://100.66.172.14:8554/labcam`: RTSP DESCRIBE returned `404 Not Found`; zero frames decoded.

Because no known live stream decoded successfully, the required five-minute live run, measured live FPS, live GPU stability, live tracking, and observed camera reconnection could not be completed.

## Zones

The current `config/zones.json` remains explicitly marked as initial approximations. It was preserved unchanged and copied locally to ignored `config/zones.rollback.json`.

Automated geometry validation confirms each approximate polygon centre maps uniquely to its own zone. Shared boundary vertices map to multiple zones, which is expected from adjacent rectangles but is not acceptable as final perspective-correct calibration. Door area, seated people, occluded areas, and real boundary behavior require a live or representative calibration image plus supervised visual validation. No final zones were guessed or saved.

## Failure Safety

- Camera-interruption code clears the partial count window.
- Attempting to calculate medians after clearing raises an error.
- Monitor validation tooling contains no MQTT import and refuses non-Monitor mode.
- No reports or false-zero reports are emitted by the live validation tool.

Status: blocked pending restoration or correction of a known RTSP source and supervised zone calibration.
