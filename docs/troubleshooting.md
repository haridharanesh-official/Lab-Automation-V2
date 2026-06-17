# Troubleshooting

- No reports: check camera URL, CUDA/model availability, broker credentials, and `vision/status`.
- Counts suddenly zero: do not act on them; camera interruption clears partial windows and must not emit a report.
- Home Assistant People Count flips between values such as `0, 2, 0, 2`: first check for duplicate publishers on `lab/vision/people_count`, then confirm HA is using debounced `lab/vision/people_count` and not diagnostic `lab/vision/raw_people_count`. The AI publisher now holds the last known good count through brief missed detections and camera uncertainty.
- Duplicate AI publisher streams on Windows: run `.\status_lab_automation.ps1` and check `ai_publisher_matching_process_count`. If it is greater than `1`, run `.\stop_lab_automation.ps1`; the stop script now removes matching orphaned `src.main --config config/config.yaml` child processes, not just the PowerShell wrapper PID.
- Raw count differs from HA People Count: this is expected. `lab/vision/raw_people_count` is current diagnostic detection data; `lab/vision/people_count` is debounced for HA and Node-RED.
- Display boxes appear but zone counts stay zero: confirm the live frame is 1280x720, `config/zones.json` uses the same coordinate space, and bottom-centre foot-point markers land inside the visible zone polygons. The display now shows current zone counts separately from stable/window counts.
- Vision unhealthy/stale: confirm timetable fallback and `lab/automation/priority_state` before trusting occupancy automation.
- `start_lab_automation.ps1 -Display` complains that `display` property is missing: remove the stale `logs/ai-publisher/ai-publisher.pid.json` file or stop the old publisher first. Newer scripts tolerate missing `display` fields from older PID files.
- Mode flips back unexpectedly: inspect for duplicate publishers on `lab/automation/mode`. In the intended v2 design, Home Assistant should publish only user mode requests, and Node-RED should publish only `lab/automation/mode_state` plus automation diagnostics.
- Manual state seems stuck: inspect `lab/automation/manual_override_state` and clear using `lab/automation/manual_override/clear`.
- Relay does not change: confirm Auto mode, valid sequence, desired-versus-confirmed difference, ESP32 online status, and non-retained `/set`.
- Relay flickers: disable Auto immediately, inspect duplicate publishers and retained `/set` messages. Legacy helpers must not inject relay `/set`; after the June 17, 2026 cleanup, `labos-automation.service` is passive and `labos-relay-ack-monitor.service` logs only.
- `labos-relay-ack-monitor.service` still logs noisy relay topic parse errors from older assumptions about `lab/control/relayX/state` and `/set` topic parsing. Treat those logs as a diagnostics cleanup item unless they are accompanied by actual injected relay commands.
- ESP32 boot issue: confirm GPIO mapping exactly matches firmware and GPIO 5 is unused.
- Recovery always starts in Manual, then Monitor, then supervised Auto.
