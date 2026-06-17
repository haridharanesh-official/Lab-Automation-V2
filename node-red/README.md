# Node-RED Flow Notes

The repo flow in [flows.json](/C:/Users/prith/Downloads/Lab%20Automation%20v2.0/node-red/flows.json) now targets the current deployed `labos` runtime MQTT contract:

- vision input under `lab/vision/...`
- automation state under `lab/automation/...`
- relay control under `lab/control/...`

Priority order implemented in the repo flow:

1. manual override
2. timetable fallback
3. healthy people-count automation

Current Auto behavior is people-count-only. The flow reads `lab/vision/people_count.stable_count` and ignores `zone_counts` for relay decisions until zone calibration is physically validated.

Stage rules:
- `0` people: controlled loads OFF only after the empty/off delay
- `1` person: both lights ON
- `2-3` people: both lights + Fan 1 + Fan 4 ON
- `4+` people: both lights + all fans ON

Manual override clear topic:

- `lab/automation/manual_override/clear`

Do not deploy this updated repo flow onto `labos` without first backing up the live flow and validating the change in Monitor mode.
