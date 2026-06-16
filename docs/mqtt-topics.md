# MQTT Topics

Current deployed Lab Automation v2.0 runtime on `labos` uses the `lab/...` namespace for AI vision telemetry.

- AI PC publishes only:
  - `lab/vision/people_count`
  - `lab/vision/status`
  - `lab/vision/source_status`
  - `lab/vision/heartbeat`

- Current deployed `labos` Node-RED flow consumes:
  - `lab/vision/people_count`
  - `lab/vision/status`
  - `lab/vision/source_status`
  - `lab/vision/heartbeat`

- AI PC is blocked from publishing:
  - `lab/control/#`
  - `lab/control/+/set`
  - any topic containing `/relay/`
  - any topic containing `/set`
  - any topic containing `/command`

Rules: AI may publish only under `lab/vision/#`; AI must never publish control or relay topics; Node-RED alone may publish physical relay commands.
