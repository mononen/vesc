---
title: "Footpad Sensor"
aliases:
  - "Footpad Sensor"
tags:
  - sensor
  - footpad
  - safety
  - engagement
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/footpad_sensor.c
  - refloat/src/footpad_sensor.h
  - refloat/src/main.c
---

# Footpad Sensor

The footpad sensor detects whether the rider's feet are on the board. It's the primary human-presence sensor — without it, the board would have no way to know if it should be balancing a rider or just sitting still.

On a onewheel, there are typically two footpad pressure sensors (one front, one rear) each connected to an ADC pin. Refloat reads these voltages and classifies the contact state.

---

## States

```c
typedef enum {
    FS_NONE,    // No foot contact on either pad
    FS_LEFT,    // Only left/front pad active
    FS_RIGHT,   // Only right/rear pad active
    FS_BOTH     // Both pads active
} FootpadSensorState;
```

The state is determined each main loop iteration by comparing raw ADC values against configured thresholds:

```
if adc1 > fault_adc1 AND adc2 > fault_adc2:  → FS_BOTH
if adc1 > fault_adc1 only:                    → FS_LEFT
if adc2 > fault_adc2 only:                    → FS_RIGHT
else:                                          → FS_NONE
```

---

## Role in Engagement

The `can_engage()` check in the state machine requires valid footpad contact before the board will enter `RUNNING` state:

**Standard (dual switch):** `FS_BOTH` required
**`startup_simplestart_enabled`:** `FS_LEFT` or `FS_RIGHT` accepted after 2 seconds in READY state
**`fault_is_dual_switch = false`:** Any single pad accepted

The footpad state also gates re-engagement after a bail — the rider must have valid contact to trigger push-start (dirty landing) recovery.

---

## Role in Fault Detection

While running, the footpad is checked every main loop cycle:

**Full switch fault (`STOP_SWITCH_FULL`):** `FS_NONE` for longer than `fault_delay_switch_full` ms → board stops. This catches the rider falling off completely.

**Half switch fault (`STOP_SWITCH_HALF`):** `FS_LEFT` or `FS_RIGHT` at low speed (below `fault_adc_half_erpm`) for longer than `fault_delay_switch_half` ms → board stops. Prevents riding one-footed at low speed.

**`fault_moving_fault_disabled`:** When true, switch faults are suppressed above a speed threshold. Useful for technical riding where footpad contact may be momentarily interrupted.

---

## Konami Sequences

The footpad sequence history is tracked by [[konami.c]] to detect secret activation patterns. Two known sequences:

**Flywheel Mode:** `LEFT, NONE, RIGHT, NONE, LEFT, NONE, RIGHT`
- Activates flywheel (self-balancing without rider) mode
- Exit: step on both pads, or tip the board over

**Headlight Toggle:** (different LEFT/RIGHT/NONE sequence)
- Toggles headlight state on compatible hardware

These sequences require tapping the footpads in a specific rhythm from the `READY` state.

---

## ADC Thresholds and Calibration

The raw ADC values (`adc1`, `adc2`) are analog voltages. Typical footpad hardware is a simple pressure-sensitive pad that changes resistance with contact, forming a voltage divider.

**`fault_adc1` / `fault_adc2`:** Voltage threshold (0.0–3.3V) above which the pad is considered "active." Too low → false triggers from pad stiffness. Too high → requires hard pressure.

**Telemetry:** `adc1` and `adc2` are included in the real-time data stream. Check these values in VESC Tool with your foot on and off the pad to find appropriate thresholds for your specific hardware.

---

## References

- [[footpad_sensor.c]] — ADC read and state classification
- [[footpad_sensor.h]] — `FootpadSensor` struct: `adc1`, `adc2`, `state` (FootpadSensorState)
- [[main.c]] — `can_engage()` lines 325–351, `check_faults()` lines 354–490
- [[refloat-config|RefloatConfig]] — `fault_adc1`, `fault_adc2`, `fault_delay_switch_full`, `fault_delay_switch_half`, `fault_adc_half_erpm`
- [[state-machine|State Machine]] — READY → RUNNING transition requires valid footpad state
- [[fault-detection|Fault Detection]] — switch fault logic using footpad state
- [[tuning-engagement|Tuning Engagement and Startup]] — how to calibrate ADC thresholds and fault delays
