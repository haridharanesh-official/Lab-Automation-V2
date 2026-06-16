# Node-RED Flow Notes

The repo flow in [flows.json](/C:/Users/prith/Downloads/Lab%20Automation%20v2.0/node-red/flows.json) now targets the current deployed `labos` runtime MQTT contract:

- vision input under `lab/vision/...`
- automation state under `lab/automation/...`
- relay control under `lab/control/...`

Priority order implemented in the repo flow:

1. manual override
2. timetable fallback
3. healthy people-count automation

Manual override clear topic:

- `lab/automation/manual_override/clear`

Do not deploy this updated repo flow onto `labos` without first backing up the live flow and validating the change in Monitor mode.
