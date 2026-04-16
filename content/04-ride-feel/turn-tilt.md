---
title: "Turn Tilt"
aliases:
  - "Turn Tilt"
tags:
  - ride-feel
  - turn-tilt
  - yaw
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/turn_tilt.c
  - refloat/src/turn_tilt.h
---

# Turn Tilt

Turn Tilt tilts the nose of the board when the rider is turning, compensating for the speed loss that occurs in a corner. Without it, carving produces a slight nosedive feeling as the effective forward component of velocity decreases. TurnTilt prevents this by raising the setpoint during turns, creating a more neutral and planted cornering feel.

---

## Yaw Rate Detection

The board's turning rate is derived from the yaw angle difference between consecutive main loop cycles:

```c
// turn_tilt.c
yaw_change = yaw - last_yaw_angle
last_yaw_angle = yaw

// Clamped to ±72°/s, then smoothed through a 25 Hz EMA
yaw_change.ema_update(yaw_change)
```

The 25 Hz EMA smooths out brief yaw spikes from road vibration. The clamp to ±72°/s prevents extreme transients from producing large tilt commands.

---

## Aggregate Yaw

Rather than responding to instantaneous yaw rate, TurnTilt accumulates yaw change over time:

```c
// turn_tilt.c
if abs(yaw_change.ema) > 0.05 degrees/s:   // Ignore noise below 0.05
    if sign(yaw_change) == sign(yaw_aggregate):
        yaw_aggregate += yaw_change * dt     // Keep accumulating in same direction
    else:
        yaw_aggregate = 0                    // Direction reversed: reset aggregate
```

The aggregate resets on direction reversal — this prevents left-then-right chicane motion from building up a large aggregate in one direction.

The aggregate reaches `turntilt_start_angle` threshold only during sustained turning. Brief road-induced yaw changes don't accumulate enough to trigger TurnTilt.

---

## Target Computation

```c
// turn_tilt.c
if abs(yaw_aggregate) > turntilt_start_angle
   AND abs_erpm > turntilt_start_erpm:

    speed_boost = turntilt_erpm_boost * abs_erpm / boost_end_erpm  // linear at speed
    
    target = turntilt_strength * yaw_aggregate * (1 + speed_boost)
    target = clamp(target, -turntilt_angle_limit, turntilt_angle_limit)
```

`turntilt_erpm_boost` provides extra correction at speed, where cornering dynamics are more pronounced and the speed-loss effect is larger. The boost scales linearly from `turntilt_erpm_boost` ERPM to `turntilt_erpm_boost_end`.

---

## Ramping

The tilt ramps toward target at `turntilt_speed` (°/s). When the turn ends (yaw aggregate returns to zero or reverses), the tilt ramps back at the same speed.

The ramp speed is the same for engagement and disengagement — smooth in, smooth out.

---

## Added Directly to Setpoint

Unlike ATR and TorqueTilt (which are arbitrated against each other), TurnTilt is **added directly** to the final setpoint regardless of other tilt contributors:

```
setpoint += turn_tilt.setpoint
```

This means TurnTilt always has its full effect, independent of ATR or TorqueTilt levels.

---

## `TurnTilt` Struct

```c
// turn_tilt.h:24–35
TurnTilt {
    float speed;              // Ramp speed (from config)
    float boost_per_erpm;    // Speed boost coefficient
    float last_yaw_angle;    // Previous yaw for delta calculation
    EMA yaw_change;          // EMA-smoothed yaw change rate
    float yaw_aggregate;     // Accumulated yaw (resets on reversal)
    float target;            // Current target tilt (degrees)
    float setpoint;          // Output: current tilt contribution (degrees)
}
```

---

## References

- [[turn_tilt.c]] — `turn_tilt_update()` lines 48–120; yaw aggregate and speed boost
- [[turn_tilt.h]] — `TurnTilt` struct lines 24–35
- [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] — source of `yaw` angle
- [[refloat-config|RefloatConfig]] — `turntilt_strength`, `turntilt_angle_limit`, `turntilt_start_angle`, `turntilt_start_erpm`, `turntilt_speed`, `turntilt_erpm_boost`, `turntilt_erpm_boost_end`, `turntilt_yaw_aggregate`
- [[setpoint-composition|Setpoint Composition]] — TurnTilt added directly to setpoint (not arbitrated)
- [[tuning-ride-feel|Tuning Ride Feel]] — TurnTilt tuning guidance
