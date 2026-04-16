---
title: "Brake Tilt"
aliases:
  - "Brake Tilt"
tags:
  - ride-feel
  - brake-tilt
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/brake_tilt.c
  - refloat/src/brake_tilt.h
---

# Brake Tilt

Brake Tilt lifts the nose slightly during active motor braking. On a onewheel, braking naturally tends to pitch the nose down (the wheel decelerates but inertia carries the front end forward). Brake Tilt counteracts this by raising the setpoint, making the board ask the rider to shift weight rearward — a more intuitive braking posture.

---

## Activation Conditions

BrakeTilt only activates when all three conditions are true:

```c
// brake_tilt.c
motor.braking == true               // Motor drawing negative current (regen)
abs_erpm > 2000                    // Moving at meaningful speed
sign(balance_offset) != sign(erpm) // Board is leaning against direction of travel
```

The third condition `sign(balance_offset) != sign(erpm_sign)` means the rider's weight is slightly behind the balance point relative to forward motion — the classic "braking lean." This filter prevents BrakeTilt from triggering during constant-speed riding where the motor happens to regen lightly.

---

## Target Computation

```c
// brake_tilt.c:45–88
factor = -(0.5 + (20 - braketilt_strength) / 5)
// Note: higher strength = smaller magnitude factor (less intuitive naming)

target = balance_offset / factor
```

The `balance_offset` is the current steady-state lean relative to the setpoint — a measure of how much the rider is pushing against the braking. Dividing by `factor` converts this into a setpoint lift proportional to braking intensity.

---

## Downhill Damping

BrakeTilt contains built-in damping for downhill braking. If `atr.accel_diff` is strongly negative (terrain is assisting, i.e., steep downhill), the BrakeTilt effect is reduced:

```c
// brake_tilt.c
downhill_factor = clamp(-atr.accel_diff / some_scale, 0, 1)
target *= (1.0 - downhill_factor)
```

On very steep descents, the nose-up from BrakeTilt would conflict with ATR's nose-down signal (ATR detects the excess acceleration as downhill). This damping prevents the two algorithms from fighting each other.

---

## Lingering

`braketilt_lingering` controls how slowly BrakeTilt decays after braking ends. The step size transitions from `atr_off_speed` to a slower rate as the motor stops braking, allowing the nose-up effect to persist briefly after the brake is released. This smooths the transition back to normal riding.

---

## `BrakeTilt` Struct

```c
// brake_tilt.h:25–30
BrakeTilt {
    float factor;              // Computed strength factor
    float target;              // Current target angle
    float ramped_step_size;    // Internal ramp state
    float setpoint;            // Output: current tilt contribution (degrees)
}
```

---

## Summed with ATR

BrakeTilt's output is **summed with ATR's output** before being arbitrated against TorqueTilt. They are not independently arbitrated:

```
combined = atr.setpoint + brake_tilt.setpoint
```

See [[setpoint-composition|Setpoint Composition]] for the full arbitration against TorqueTilt.

---

## References

- [[brake_tilt.c]] — `brake_tilt_update()` lines 45–88; downhill damping logic
- [[brake_tilt.h]] — `BrakeTilt` struct lines 25–30
- [[motor-data|Motor Data]] — `motor.braking`, `motor.dir_current`
- [[atr|ATR — Adaptive Terrain Response]] — `atr.accel_diff` used for downhill damping; summed with BrakeTilt
- [[refloat-config|RefloatConfig]] — `braketilt_strength`, `braketilt_lingering`
- [[setpoint-composition|Setpoint Composition]] — BrakeTilt + ATR arbitration against TorqueTilt
- [[tuning-ride-feel|Tuning Ride Feel]] — BrakeTilt tuning guidance
