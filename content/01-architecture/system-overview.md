---
title: "System Overview"
aliases:
  - "System Overview"
tags:
  - architecture
  - refloat
  - bldc
  - overview
date: 2026-04-16
source_files:
  - refloat/src/main.c
  - refloat/vesc_pkg_lib/vesc_c_if.h
---

# System Overview

A VESC-based onewheel is two codebases working together: bldc (the motor controller firmware) runs on the microcontroller hardware and owns the motor and IMU at the hardware level. Refloat is a VESC package — a compiled plugin — that runs inside bldc as a guest, using bldc's APIs to read sensors and command the motor.

---

## The Two Codebases

**bldc** — VESC open-source motor controller firmware
- Runs on STM32 microcontroller (ARM Cortex-M4)
- Manages [[foc-overview|FOC Overview]] at ~20 kHz
- Manages IMU hardware and runs its own [[mahony-ahrs-filter|Mahony AHRS Filter]]
- Manages communication (USB, UART, CAN)
- Exposes a function-pointer API (`vesc_c_if`) for external packages

**Refloat** — Self-balancing controller package
- Compiled into a `.vescpkg` file, loaded by bldc at runtime
- Reads IMU angles via callback hook into bldc's IMU interrupt
- Commands motor current via `VESC_IF->mc_set_current()`
- Runs its own [[mahony-ahrs-filter|Mahony AHRS Filter]] in parallel (for better control over filter parameters)
- Contains all the ride-feel algorithms: [[pid-controller|PID Controller]], [[atr|ATR — Adaptive Terrain Response]], [[torque-tilt|Torque Tilt]], [[brake-tilt|Brake Tilt]], [[turn-tilt|Turn Tilt]], [[Booster]]

---

## The Two Control Loops

Refloat operates two loops at different rates:

### IMU Callback (~20–30 kHz) — `imu_ref_callback()`
The critical inner loop. Registered as a callback into bldc's IMU interrupt service routine, so it runs at the same rate as the IMU hardware update.

What happens here:
1. [[mahony-ahrs-filter|Mahony AHRS Filter]] update → quaternion → `balance_pitch`, `pitch_rate`
2. [[pid-controller|PID Controller]] computes motor current from `setpoint - balance_pitch`
3. [[Booster]] adds current for large-angle stabilization
4. `VESC_IF->mc_set_current()` sends the command to bldc's FOC loop

This is where balance actually happens. Latency here directly affects stability.

### Main Thread (~1000 Hz) — `refloat_thd()`
The slower outer loop. Runs as a [[thread-model|ChibiOS]] thread.

What happens here:
1. Motor telemetry update (ERPM, current, voltage, temperature)
2. Footpad sensor read
3. Remote input read
4. Tilt algorithm updates: [[atr|ATR — Adaptive Terrain Response]], [[torque-tilt|Torque Tilt]], [[brake-tilt|Brake Tilt]], [[turn-tilt|Turn Tilt]], nose angling
5. Setpoint computation — combines all tilt contributions into the `setpoint` that the IMU callback uses
6. Fault checking and state machine transitions
7. LED, beeper, data recording updates

The setpoint computed here is consumed by the IMU callback — the two loops share state through the `Data` struct.

---

## The `Data` Struct as Shared State

All subsystem state lives in a single `Data` struct (`data.h:47`). The main thread writes setpoint and sensor data; the IMU callback reads it and writes motor commands. This is the coupling point between the two loops.

Key fields:
- `Data.setpoint` — the angle target, written by main thread, read by IMU callback
- `Data.imu.balance_pitch` — written by IMU callback's Mahony filter, read by PID
- `Data.motor` — ERPM, current, etc., written by main thread, read by ATR, booster, etc.
- `Data.state` — run state, written by main thread based on fault checks

---

## Package Model

Refloat uses bldc's `vesc_c_if.h` function pointer table as its entire API boundary. Every call Refloat makes to the hardware goes through this table:

```c
VESC_IF->mc_set_current(current)        // Command motor
VESC_IF->mc_get_rpm()                   // Read ERPM
VESC_IF->imu_startup_done()             // Check IMU ready
VESC_IF->set_imu_process_callback(fn)   // Hook IMU interrupt
VESC_IF->request_value(VESC_VALUE_...)  // Read any telemetry
```

This abstraction means Refloat is hardware-agnostic — it runs on any VESC hardware variant without modification.

---

## References

- [[refloat/src/main.c]] — `imu_ref_callback()` line 765, `refloat_thd()` line 788
- [[data.h]] — `Data` struct, central shared state, lines 47–136
- [[thread-model|Thread Model and Timing]] — ChibiOS thread structure and priorities
- [[refloat-bldc-interface|Refloat–BLDC Interface]] — `vesc_c_if` API in detail
- [[data-flow|Data Flow: From Sensor to PWM]] — end-to-end trace of one control cycle
