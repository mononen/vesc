---
title: "Setpoint Composition"
aliases:
  - "Setpoint Composition"
  - "Setpoint"
tags:
  - control
  - setpoint
  - architecture
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/main.c
---

# Setpoint Composition

The setpoint is the angle the [[pid-controller|PID Controller]] is trying to hold. It is not fixed at zero — it is continuously updated by the main thread at 1 kHz, combining contributions from safety pushbacks, terrain adaptation, rider input, and turning behavior.

Understanding setpoint composition is understanding how all the ride-feel algorithms actually affect motor output.

---

## The Final Formula

```
setpoint = setpoint_target_interpolated   // Base: tiltback, SAT state
         + remote.setpoint                // Remote/inputtilt contribution
         + noseangling_interpolated       // Speed-dependent nose angle
         + turn_tilt.setpoint             // Yaw-rate-based turn compensation
         + arbitrate(
               atr.setpoint + brake_tilt.setpoint,   // Terrain group
               torque_tilt.setpoint                   // Current group
           )
```

Each component is computed independently, then combined here each main loop cycle. The PID reads `data.setpoint` in the IMU callback.

---

## Base Setpoint — `setpoint_target`

Computed by `calculate_setpoint_target()` in `main.c:492–706`.

At normal riding conditions with no active safety conditions: `setpoint_target = 0` (level).

When a `SetpointAdjustmentType (SAT)` is active, the base setpoint moves to the tiltback angle:

| SAT State | Base Setpoint |
|-----------|--------------|
| `SAT_CENTERING` | Moves toward 0 at `startup_speed` |
| `SAT_PB_DUTY` | Moves to `tiltback_duty_angle` at `tiltback_duty_speed` |
| `SAT_PB_SPEED` | Moves to `tiltback_duty_angle` at `tiltback_duty_speed` |
| `SAT_PB_HIGH_VOLTAGE` | Moves to `tiltback_hv_angle` at `tiltback_hv_speed` |
| `SAT_PB_LOW_VOLTAGE` | Moves to `tiltback_lv_angle` at `tiltback_lv_speed` |
| `SAT_PB_TEMPERATURE` | Moves to `tiltback_duty_angle` at `tiltback_duty_speed` |

The `setpoint_target_interpolated` is a rate-limited version of `setpoint_target` — it ramps toward the target rather than snapping to it.

---

## Noseangling — `noseangling_interpolated`

Computed by `apply_noseangling()` in `main.c:708–722`.

A speed-dependent nose angle that builds linearly with ERPM above a threshold:

```
variable_component = tiltback_variable * max(0, abs_erpm - tiltback_variable_erpm)
                     * sign(erpm)
                     * clamp to tiltback_variable_max

constant_component = tiltback_constant  (if abs_erpm > tiltback_constant_erpm)

noseangling = variable_component + constant_component
noseangling_interpolated ← rate-limited toward noseangling at noseangling_speed
```

This creates a natural cruise-control effect: the faster you go, the more the nose tilts back, discouraging more speed without a harsh pushback.

---

## Turn Tilt — Direct Addition

`turn_tilt.setpoint` is added directly to the combined setpoint. [[turn-tilt|Turn Tilt]] is independent of the ATR/TorqueTilt arbitration — it is always summed in.

---

## ATR + BrakeTilt vs TorqueTilt — The Arbitration

This is the most non-obvious part of setpoint composition. The three terrain/current tilts are **not simply added** together.

Two groups:
- **Group A:** `atr.setpoint + brake_tilt.setpoint` (terrain + braking feel)
- **Group B:** `torque_tilt.setpoint` (raw current feedback)

These groups are arbitrated:

```c
// main.c:955–961
float ab = atr.setpoint + brake_tilt.setpoint;
float tt = torque_tilt.setpoint;

if (sign(ab) == sign(tt)) {
    // Same direction: use whichever is larger
    setpoint += sign(ab) * max(abs(ab), abs(tt));
} else {
    // Opposing directions: add both
    setpoint += ab + tt;
}
```

**Why this logic?**

ATR and TorqueTilt often want to tilt in the same direction (both want nose-up during uphill acceleration). If both were summed naively, their effects would double up and cause excessive tilt. The arbitration instead takes the dominant signal when they agree.

When they disagree (e.g., ATR wants nose-up due to terrain, but TorqueTilt wants nose-down because the rider is braking), both signals are meaningful and different — so they're added.

**Practical implication for tuning:** You cannot double the effect of both ATR and TorqueTilt simultaneously on uphill acceleration — only the stronger one wins. If you want more tilt in that scenario, increase the stronger parameter.

---

## Wheelslip Override

During wheelslip (detected in main thread), the setpoint update is suspended and all tilt contributions are wound down toward zero:

```c
if (state.wheelslip) {
    // Wind down all tilt setpoints by 0.5% per cycle
    torque_tilt.setpoint *= 0.995;
    atr.setpoint *= 0.995;
    brake_tilt.setpoint *= 0.995;
    turn_tilt.setpoint *= 0.995;
    // setpoint stays at last value before wheelslip
}
```

The PID continues running during wheelslip (with the last good setpoint), but motor current is zeroed via traction control.

---

## Remote Input

`remote.setpoint` is a lean angle commanded from an external input (UART or PPM remote). It's added directly to the setpoint, allowing remote-controlled tilt adjustment. Most riders don't use this; it's primarily for assistive use cases.

---

## References

- [[main.c]] — `calculate_setpoint_target()` lines 492–706, `apply_noseangling()` lines 708–722, setpoint combination lines 912–962
- [[atr|ATR — Adaptive Terrain Response]] — produces `atr.setpoint`
- [[brake-tilt|Brake Tilt]] — produces `brake_tilt.setpoint`
- [[torque-tilt|Torque Tilt]] — produces `torque_tilt.setpoint`
- [[turn-tilt|Turn Tilt]] — produces `turn_tilt.setpoint`
- [[nose-angling|Nose Angling and Pushback Speed Control]] — produces `noseangling_interpolated`
- [[pushback-tiltback|Pushback and Tiltback System]] — produces `setpoint_target`
- [[pid-controller|PID Controller]] — consumes the final `setpoint`
- [[traction-control|Traction Control and Wheelslip]] — overrides setpoint updates during wheelslip
