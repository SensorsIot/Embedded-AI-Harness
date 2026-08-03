# Canonical test-specification schema

Every generated test uses this schema. A test missing `pass_criteria`,
`required_evidence`, or `cleanup` is not a specification — it is a suggestion.

For the human-readable document these specs are rendered into (section order,
preamble, matrix layout), see `test-spec/document-format.md` and its templates.

```yaml
id:
title:
requirements:          # the FSD clause IDs this verifies
purpose:
priority:              # must | should | may
tier:                  # host | target | bench
kind:                  # positive | negative | boundary | state-transition | error | persistence | recovery | timeout | security | performance

preconditions:
initial_state:
test_data:
equipment:
interfaces:

stimulus:
expected_observations:
prohibited_outcomes:
timing:
tolerances:

pass_criteria:
failure_criteria:
required_evidence:

cleanup:
failure_recovery:
dependencies:

automation:
  feasible:
  framework:
  suggested_driver:
  required_workbench_capabilities:
  required_test_seams:

implementation_handoff:
  suggested_test_file:
  related_components:
  notes:
```

## Field notes

- **`prohibited_outcomes`** — outcomes that invalidate a pass even when every
  expected observation occurred. A recovery test without this passes when the
  device recovers *by rebooting*, which is usually the defect under test.
- **`failure_criteria`** — stated explicitly, not inferred as "not pass". It tells
  the operator when to stop waiting.
- **`required_evidence`** — what is captured to prove the result. Without it a
  pass is an assertion, not a record.
- **`failure_recovery`** — what to do when the test fails, in order. Capture
  evidence *before* resetting anything; a reset destroys the reset reason.
- **`required_test_seams`** — hooks the firmware must expose for this test to be
  feasible. Empty means none. Non-empty is a handoff obligation to development,
  and belongs in the implementation handoff, not discovered at test-writing time.

## Example

```yaml
id: TC-MQTT-08
title: Resume telemetry after broker interruption
requirements:
  - FR-MQTT-08
purpose: >
  Verify automatic MQTT recovery without restarting the DUT.
priority: must
tier: bench
kind: state-transition

preconditions:
  - DUT is powered.
  - DUT is connected to the workbench WiFi AP.
  - DUT is publishing valid telemetry.
  - MQTT broker is running.

initial_state:
  dut: operational
  wifi: connected
  mqtt: connected
  broker: running

test_data:
  interruption_s: 10
  recovery_limit_s: 30
  telemetry_topic: gplug/test-device/power

equipment:
  - Embedded Workbench
  - ESP32 DUT

interfaces:
  - WiFi
  - MQTT
  - serial-or-udp-log

stimulus:
  - Stop the MQTT broker.
  - Keep it stopped for 10 s.
  - Restart the broker.

expected_observations:
  - MQTT loss is detected.
  - WiFi remains connected throughout.
  - A new MQTT connection is established.
  - A valid numeric telemetry payload is received within 30 s.

prohibited_outcomes:
  - DUT reboot.
  - Manual provisioning required.
  - A stale or invalid payload accepted as recovery evidence.

timing: 30 s from broker restart to first valid telemetry
tolerances: ±5 s

pass_criteria:
  - All expected observations occur within their limits.
  - No prohibited outcome occurs.

failure_criteria:
  - No valid telemetry within 30 s of broker restart.
  - DUT restarts, or requires operator intervention.

required_evidence:
  - Broker stop and start timestamps.
  - First telemetry event after recovery.
  - Reset reason or boot counter.
  - Diagnostic log excerpt.

cleanup:
  - Ensure the broker is running.
  - Remove temporary subscriptions.
  - Restore the operational baseline.

failure_recovery:
  - Start the broker if stopped.
  - Capture evidence first; reset the DUT only afterwards.

dependencies: []

automation:
  feasible: true
  framework: pytest
  suggested_driver: WorkbenchDriver
  required_workbench_capabilities:
    - mqtt_start
    - mqtt_stop
    - serial_monitor
  required_test_seams: []

implementation_handoff:
  suggested_test_file: tests/bench/test_mqtt_recovery.py
  related_components:
    - mqtt-manager
    - telemetry-publisher
```
