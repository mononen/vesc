---
title: "Nose Angling and Pushback Speed Control"
aliases:
  - "Nose Angling and Pushback Speed Control"
tags:
  - ride-feel
  - nose-angling
  - speed
  - tiltback
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/main.c
  - refloat/src/conf/datatypes.h
---

# Nose Angling and Pushback Speed Control

Nose angling creates a speed-dependent angle bias in the board — as the rider goes faster, the nose gradually tilts back more, making it progressively harder to accelerate further. This is the "cruise control" effect: the board guides the rider toward a comfortable maximum speed without the harsh nose-snap of emergency pushback.

---

## Variable Tiltback

The primary nose-angling mechanism scales linearly with ERPM above a threshold:

```c
// main.c:708–722 apply_noseangling()
variable_erpm = abs_erpm - tiltback_variable_erpm   // How far above threshold
variable_erpm = max(0, variable_erpm)               // Clamp to positive

noseangling_target = tiltback_variable * variable_erpm * sign(erpm)
noseangling_target = clamp(noseangling_target, -tiltback_variable_max, tiltback_variable_max)
```

`tiltback_variable` is in units of degrees per ERPM above threshold. Since ERPM for a onewheel can reach 10,000+, even tiny values (e.g., 0.0003) produce meaningful angles at speed.

`tiltback_variable_erpm` sets where the ramp starts. Setting it to 3000 ERPM means the board rides flat below 3000 ERPM and starts tilting back above that.

`tiltback_variable_max` caps the maximum nose angle from variable tiltback, preventing it from getting unreasonably steep at very high speeds.

---

## Constant Tiltback

A fixed nose angle added above a second speed threshold:

```c
if abs_erpm > tiltback_constant_erpm:
    noseangling_target += tiltback_constant * sign(erpm)
```

This creates a distinct step in the nose angle at a specific speed. Often used as an additional clear signal — "you've crossed this speed line" — on top of the gradual variable ramp.

`tiltback_constant` is in degrees. Setting it to 1–2° at a specific ERPM creates a gentle but noticeable additional push.

---

## Rate Limiting

The combined `noseangling_target` (variable + constant) is rate-limited before being applied:

```c
noseangling_interpolated ← rate_limit(noseangling_target, noseangling_speed, dt)
```

`noseangling_speed` (°/s) controls how quickly the nose angle changes as speed changes. A low value (1–2 °/s) means the nose lags well behind actual speed — gentle and smooth. A higher value (8–10 °/s) tracks speed more tightly — more immediate.

The rate limit applies in both directions: when speeding up (nose rises) and when slowing down (nose returns to flat). Riders who want the nose to return to flat quickly on deceleration should use a higher `noseangling_speed`.

---

## Distinction from Pushback

**Noseangling** is a continuous, proportional bias that builds gradually with speed. The rider barely notices it individually — it just makes the board progressively harder to push faster.

**Pushback/Tiltback** (see [[pushback-tiltback|Pushback and Tiltback System]]) is an urgent binary response — when a safety threshold is exceeded, the nose snaps toward a target angle at a fixed speed. It's noticeable and intentional.

Both are expressed as setpoint contributions, but they serve different purposes:
- Noseangling = "Here's a comfortable speed limit"
- Pushback = "You've exceeded a limit, slow down now"

Both can be active simultaneously. The noseangling is added to the base setpoint, and pushback moves the base setpoint target — they stack.

---

## Backward Riding

`sign(erpm)` in the noseangling formula means the nose angle direction flips when riding backward:
- Forward: nose rises as speed increases
- Backward: nose rises (from the rider's perspective — it's the trailing end of the board) as backward speed increases

This ensures the speed-limiting guidance works symmetrically in both directions.

---

## References

- [[main.c]] — `apply_noseangling()` lines 708–722
- [[refloat-config|RefloatConfig]] — `tiltback_variable`, `tiltback_variable_erpm`, `tiltback_variable_max`, `tiltback_constant`, `tiltback_constant_erpm`, `noseangling_speed`
- [[setpoint-composition|Setpoint Composition]] — `noseangling_interpolated` added to setpoint
- [[pushback-tiltback|Pushback and Tiltback System]] — urgent safety tiltbacks vs gradual noseangling
- [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] — practical configuration guidance
