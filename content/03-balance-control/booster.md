---
title: "Booster"
aliases:
  - "Booster"
tags:
  - control
  - booster
  - tuning
  - stiffness
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/booster.c
  - refloat/src/booster.h
---

# Booster

The Booster is a nonlinear current injection that adds extra motor current when the board's pitch error exceeds a configurable threshold. It provides a "wall of stiffness" at large lean angles without making normal riding feel harsh.

Unlike the [[pid-controller|PID Controller]]'s P term (which is linear), the Booster only activates above a threshold — the board feels normal within the threshold angle, then firms up sharply beyond it.

---

## How It Works

The booster computes a proportional term from a slightly different pitch signal than the PID uses:

```c
// booster.c
proportional = setpoint - brake_tilt.setpoint - pitch
// Note: uses raw pitch, not balance_pitch
```

This proportional value is compared against `booster_angle`:

```
if abs(proportional) < booster_angle:
    booster_target = 0          // Within threshold, no boost
else:
    // Linear ramp beyond threshold
    booster_target = sign(proportional) * (abs(proportional) - booster_angle) * booster_ramp
    booster_target = clamp(booster_target, -booster_current, booster_current)
```

The result is smoothed through a 1 Hz EMA before being added to the PID output.

---

## `booster_current` vs PID Output

The booster adds directly to the motor current command, after the PID:

```c
new_current = (pid.p + pid.i + pid.rate_p + booster.current_ema) * softstart_limit
```

Both the PID output and the booster current share the same absolute current clamp (`current_max`). If the motor is already at its current limit due to PID output, booster current is clipped.

This means booster is most effective during moderate lean angles (where PID hasn't maxed out yet) and less effective during extreme dives (where PID is already at the current limit).

---

## Braking Booster

Separate parameters exist for the braking direction:

```c
brkbooster_angle    // Threshold for braking booster activation
brkbooster_ramp     // Ramp rate (A per degree beyond threshold)
brkbooster_current  // Maximum braking boost current
```

The forward and braking boosters can be tuned independently. Many riders increase `brkbooster_current` to prevent nosedive during hard braking at the limits.

---

## Effect on Ride Feel

**Without booster:** The PID provides linear resistance at all angles. At large angles (near a fall), the resistance isn't disproportionately higher than at small angles — the board has no "last resort" stiffness.

**With booster:** Normal riding (within `booster_angle`) feels identical to no-booster. At large lean angles (beyond `booster_angle`), there's an additional firm push-back that feels like the board doesn't want to go further. Riders describe this as the board "feeling planted" at the limits.

---

## `Booster` Struct

```c
// booster.h
Booster {
    EMA current;   // EMA-smoothed booster output (the actual addition to motor current)
}
```

---

## References

- [[booster.c]] — `booster_update()` lines 37–80; threshold check, ramp, EMA
- [[booster.h]] — `Booster` struct
- [[pid-controller|PID Controller]] — booster current added to PID output before final motor command
- [[refloat-config|RefloatConfig]] — `booster_angle`, `booster_ramp`, `booster_current`, `brkbooster_*`
- [[tuning-ride-feel|Tuning Ride Feel]] — booster tuning in context of all ride-feel algorithms
