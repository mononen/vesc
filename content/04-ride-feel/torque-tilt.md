---
title: "Torque Tilt"
aliases:
  - "Torque Tilt"
tags:
  - ride-feel
  - torque-tilt
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/torque_tilt.c
  - refloat/src/torque_tilt.h
---

# Torque Tilt

Torque Tilt tilts the nose of the board proportional to filtered motor current. Accelerating hard tilts the nose up; braking tilts it down (tail-up). This provides natural haptic feedback — the board's physical angle reflects the forces being applied, making acceleration and braking feel intuitive.

---

## Mechanism

```c
// torque_tilt.c:41–78
current_above_threshold = max(0, abs(filt_current) - torquetilt_start_current)

strength = braking ? torquetilt_strength_regen : torquetilt_strength

target = clamp(
    current_above_threshold * strength * sign(dir_current),
    -torquetilt_angle_limit,
    torquetilt_angle_limit
)
```

`filt_current` is `motor.filt_current` — the Biquad-filtered directional current. Using the filtered version prevents high-frequency current spikes (from PWM noise or brief load changes) from causing twitchy tilt.

`sign(dir_current)` gives the direction: positive current (accelerating) → positive tilt target (nose up). Negative current (braking/regen) → negative tilt target (nose down / tail up).

`torquetilt_start_current` acts as a deadband — the board doesn't react to small currents (e.g., just holding balance). Only current above this threshold contributes to the tilt.

---

## Ramping

The tilt doesn't snap to the target — it ramps at configurable speeds:

```c
if sign(target) != sign(current_setpoint):
    step_size = max(off_speed, on_speed) * dt   // Faster when crossing zero
elif abs(target) < abs(current_setpoint):
    step_size = off_speed * dt                  // Decreasing: off speed
else:
    step_size = on_speed * dt                   // Increasing: on speed

if abs_erpm < 500:
    step_size /= 2   // Half ramp speed at very low ERPM
```

The asymmetry between `on_speed` and `off_speed` allows fast engagement (when you accelerate, the tilt responds quickly) and slow decay (when you ease off, the tilt lingers slightly before returning).

---

## Regen Strength

`torquetilt_strength_regen` controls the tilt effect during regenerative braking separately from acceleration. This allows you to tune:
- Nose-up during forward acceleration: controlled by `torquetilt_strength`
- Tail-up (nose-down) during braking: controlled by `torquetilt_strength_regen`

Setting `strength_regen = 0` disables TorqueTilt during braking while keeping it active during acceleration.

---

## Arbitration with ATR and BrakeTilt

TorqueTilt is arbitrated against the combined ATR+BrakeTilt signal in [[setpoint-composition|Setpoint Composition]]:

- If TorqueTilt and the ATR+BrakeTilt sum point in the same direction: the **larger** of the two wins
- If they point in opposite directions: they are **added**

This means on uphill acceleration (where both ATR and TorqueTilt want nose-up), only the dominant signal contributes. Increasing both ATR and TorqueTilt won't double the effect — only the stronger one is used.

---

## `TorqueTilt` Struct

```c
// torque_tilt.h:24–30
TorqueTilt {
    float on_speed, off_speed;    // Ramp speeds (from config, in °/s)
    float ramped_step_size;       // Internal: current ramp state
    float setpoint;               // Output: current tilt contribution (degrees)
}
```

---

## References

- [[torque_tilt.c]] — `torque_tilt_update()` lines 41–78
- [[torque_tilt.h]] — `TorqueTilt` struct lines 24–30
- [[motor-data|Motor Data]] — `MotorData.filt_current` (Biquad-filtered directional current)
- [[refloat-config|RefloatConfig]] — `torquetilt_start_current`, `torquetilt_strength`, `torquetilt_strength_regen`, `torquetilt_on_speed`, `torquetilt_off_speed`, `torquetilt_angle_limit`
- [[setpoint-composition|Setpoint Composition]] — arbitration logic with ATR and BrakeTilt
- [[atr|ATR — Adaptive Terrain Response]] — arbitrated against TorqueTilt
- [[tuning-ride-feel|Tuning Ride Feel]] — TorqueTilt tuning in context
