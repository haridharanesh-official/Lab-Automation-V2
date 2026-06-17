# MQTT Topics

Current deployed Lab Automation v2.0 runtime on `labos` uses the `lab/...` namespace for AI vision telemetry.

- AI PC publishes only:
  - `lab/vision/people_count`
  - `lab/vision/raw_people_count`
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

## People Count Contract

`lab/vision/people_count` is the stable/debounced count for Home Assistant and Node-RED. It carries:

- `stable_count` and `total_count`: the debounced count used by HA and automation.
- `zone_counts`: debounced zone counts for display/debug only during the current people-count Auto phase.
- `raw_total_count` and `raw_zone_counts`: the current detection values included for context.
- `window_stable_count` and `window_zone_counts`: the rolling reporting-window median values.
- `counting_mode`: `total-count` or `zone-count`.

Counting modes:

- `total-count`: AI runs on the full frame, counts total people, does not require valid zone polygons, publishes `stable_count`, and sets zone fields to `null`.
- `zone-count`: AI runs on the full frame, assigns people to zones by bottom-centre point, publishes `stable_count` and `zone_counts`, and requires `config/zones.json`.

Current Auto logic on `labos` uses only `stable_count`:

- `0` people: all controlled loads OFF only after empty/off delay.
- `1` person: both lights ON.
- `2-3` people: both lights + Fan 1 + Fan 4 ON.
- `4+` people: both lights + all fans ON.

Zone mapping remains provisional and must not be used for production relay decisions until zone-by-zone validation passes.

`lab/vision/raw_people_count` is a diagnostic topic. It may change faster because it represents the current detection frame/window and must not be used as the primary Home Assistant people-count sensor or automation trigger.

The AI publisher holds the last known good debounced count through brief missed detections and camera/AI uncertainty. It does not publish an immediate false zero when a single frame or short run misses visible people.

## Legacy / Hardware Spec Namespace
The original hardware spec for the ESP32 relays uses `labos/v2/...`. This namespace is maintained on the hardware side for backwards compatibility and original design specifications, but the active runtime telemetry mapping is strictly `lab/...`.
