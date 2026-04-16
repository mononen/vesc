---
title: "Motor Data and Telemetry"
aliases:
  - "Motor Data and Telemetry"
  - "Motor Data"
tags:
  - motor
  - telemetry
  - data
  - filters
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/motor_data.c
  - refloat/src/motor_data.h
---

# Motor Data and Telemetry

The `MotorData` struct aggregates all motor telemetry that Refloat reads from bldc each main loop cycle. It provides the raw sensor data that ride-feel algorithms (ATR, TorqueTilt, etc.) and safety systems use for decisions.

---

## The `MotorData` Struct

```c
// motor_data.h:30–67
MotorData {
    // Speed
    float erpm;           // Electrical RPM (signed: positive = forward)
    float abs_erpm;       // |erpm|
    int8_t erpm_sign;     // +1 or -1
    EMA abs_erpm_smooth;  // EMA-smoothed abs_erpm for tiltback logic
    float speed;          // Speed in km/h
    float distance;       // Total accumulated distance

    // Current
    float current;        // Raw motor current from BLDC (A)
    float dir_current;    // current * erpm_sign (positive = torque in direction of travel)
    Biquad filt_current;  // Low-pass Biquad-filtered dir_current
    bool braking;         // true if dir_current < 0
    bool forward;         // true if erpm > 0

    // Power
    EMA duty_cycle;       // EMA-smoothed duty cycle (0.0–1.0)

    // Acceleration
    SMA acceleration;     // 40-sample SMA of ERPM delta

    // Thermal
    float mosfet_temp;    // MOSFET temperature (°C)
    float motor_temp;     // Motor temperature (°C)

    // Electrical
    float current_min;    // Motor's configured minimum current
    float current_max;    // Motor's configured maximum current
    float batt_voltage;   // Battery voltage (V)
    float lv_threshold;   // Low-voltage tiltback threshold
    float hv_threshold;   // High-voltage tiltback threshold
    float batt_current;   // Battery (input) current
}
```

---

## Key Derived Quantities

### Directional Current (`dir_current`)

```c
dir_current = current * erpm_sign
```

Raw `current` from bldc is always the magnitude of motor current, not direction-aware. By multiplying by `erpm_sign`, `dir_current` is positive when the motor is accelerating (torque in the direction of travel) and negative when braking (regenerating, opposing motion).

`dir_current` is what ATR and TorqueTilt use for their "is the motor accelerating or braking" logic.

### Filtered Current (`filt_current`)

```c
filt_current = biquad_filter(dir_current, cutoff_hz=atr_filter)
```

A Biquad (second-order IIR) low-pass filter applied to `dir_current`. The cutoff frequency is set by `RefloatConfig.atr_filter` — this is a shared filter used by both [[atr|ATR — Adaptive Terrain Response]] and [[torque-tilt]].

Lower `atr_filter` Hz = more smoothing = less noise-driven reaction from both ATR and TorqueTilt. The single filter parameter affects both algorithms.

### Acceleration (`acceleration.sma`)

```c
acceleration.sma = SMA_40(erpm - previous_erpm) / dt
```

A 40-sample simple moving average of ERPM change rate. This is the "measured acceleration" that ATR compares against expected acceleration.

The SMA uses 40 samples (~40ms at 1kHz) to average out PWM-frequency noise in the ERPM signal. Shorter window = noisier but more responsive; longer = smoother but laggy.

### Braking Flag

```c
braking = (dir_current < -some_threshold) && (abs_erpm > min_speed)
```

True when the motor is actively regenerating. Used by [[brake-tilt|Brake Tilt]] for its activation condition and by [[torque-tilt|Torque Tilt]] to select `torquetilt_strength_regen` vs `torquetilt_strength`.

---

## Update Rate

`motor_data_update()` is called once per main loop cycle (~1 kHz). It reads from the `VESC_IF` API which returns the most recent values from the FOC ISR (updated at 20 kHz). The motor data is thus effectively at 1 kHz resolution for Refloat's algorithms, even though the underlying hardware is faster.

---

## Real-Time Telemetry

These values are transmitted in the real-time data stream (`REALTIME_DATA`) to VESC Tool:

- `erpm`, `speed`, `duty_cycle`, `batt_voltage`
- `current`, `filt_current`, `dir_current`
- `mosfet_temp`, `motor_temp`
- `atr.accel_diff`, `motor.acceleration` (derived)

This is the data that appears in VESC Tool's live charts during riding. Useful for tuning — you can watch `atr.accel_diff` on a hill to calibrate ATR, or watch `filt_current` to understand TorqueTilt behavior.

---

## References

- [[motor_data.h]] — `MotorData` struct lines 30–67
- [[motor_data.c]] — `motor_data_update()`, Biquad filter application, SMA computation
- [[refloat-bldc-interface|Refloat–BLDC Interface]] — `VESC_IF->mc_get_*()` calls that populate this struct
- [[atr|ATR — Adaptive Terrain Response]] — uses `filt_current`, `acceleration.sma`
- [[torque-tilt|Torque Tilt]] — uses `filt_current`, `dir_current`
- [[brake-tilt|Brake Tilt]] — uses `braking`, `dir_current`
- [[traction-control|Traction Control and Wheelslip]] — uses `acceleration.sma`, `duty_cycle`
- [[refloat-config|RefloatConfig]] — `atr_filter` Hz sets the Biquad cutoff
