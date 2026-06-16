# Safe Operation Guidelines

**Warning**: Lab Automation v2.0 is an active hardware control project. Safety is paramount.

## Safety Rules

1. **Final Safe Mode is Manual**:
   If the system acts unexpectedly, immediately set the mode to `manual` via MQTT or Home Assistant.
   ```bash
   mosquitto_pub -h labos -t lab/automation/mode -r -m manual
   ```

2. **AI Cannot Control Relays**:
   The AI PC is physically and logically blocked from publishing relay commands (`/set`). It only publishes telemetry to `lab/vision/#`.

3. **Auto Requires Supervision**:
   Until the final physical production-readiness sign-off is given, `auto` mode must only be enabled while an operator is present in the lab observing the physical relays and lights.

4. **Monitor Mode for Diagnostics**:
   Use `monitor` mode to view intended states without actually firing physical relays.

5. **Secrets Management**:
   Never commit `.env` files, passwords, camera URLs with credentials, or Wi-Fi SSIDs to this repository. All credentials should be stored securely on the host machines (e.g., in `~/.config/` or `esp32` local changes).
