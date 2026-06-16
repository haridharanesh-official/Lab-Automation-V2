# Troubleshooting

- No reports: check camera URL, CUDA/model availability, broker credentials, and `vision/status`.
- Counts suddenly zero: do not act on them; camera interruption clears partial windows and must not emit a report.
- Vision unhealthy/stale: confirm timetable fallback and `lab/automation/priority_state` before trusting occupancy automation.
- Mode flips back unexpectedly: inspect for duplicate publishers on `lab/automation/mode`. In the intended v2 design, Home Assistant should publish only user mode requests, and Node-RED should publish only `lab/automation/mode_state` plus automation diagnostics.
- Manual state seems stuck: inspect `lab/automation/manual_override_state` and clear using `lab/automation/manual_override/clear`.
- Relay does not change: confirm Auto mode, valid sequence, desired-versus-confirmed difference, ESP32 online status, and non-retained `/set`.
- Relay flickers: disable Auto immediately, inspect duplicate publishers and retained `/set` messages. Legacy helpers must not inject relay `/set`; after the June 17, 2026 cleanup, `labos-automation.service` is passive and `labos-relay-ack-monitor.service` logs only.
- ESP32 boot issue: confirm GPIO mapping exactly matches firmware and GPIO 5 is unused.
- Recovery always starts in Manual, then Monitor, then supervised Auto.
