---
title: "PID Controller"
aliases:
  - "PID Controller"
  - "PID"
tags:
  - control
  - pid
  - balancing
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/pid.c
  - refloat/src/pid.h
  - refloat/src/main.c
---

# PID Controller

The PID controller is the core of the balancing algorithm. Every ~50 µs, it computes a motor current command based on how far the board is tilted from its target angle and how fast it's tilting. Everything else in Refloat (ATR, TorqueTilt, etc.) adjusts the *target angle* — the PID is what actually produces the motor current that keeps the board balanced.

---

## The Inverted Pendulum

A onewheel is a classic inverted pendulum. The wheel is the pivot; the board+rider system is the arm. The natural tendency is to fall. The motor must continuously correct by accelerating the wheel in the direction of the fall, creating an inertial reaction that pushes the board back upright.

The PID controller implements this correction.

---

## Control Law

Implemented in `pid_control()` called from `imu_ref_callback()`:

```c
error = setpoint - balance_pitch          // How far from target (degrees)

P      = kp  * error * scale             // Proportional: restoring force
I     += ki  * error * dt * scale        // Integral: drift correction (clamped by ki_limit)
rate_P = kp2 * (-pitch_rate) * scale     // Rate-P: angular velocity damping

output = P + I + rate_P
```

The `scale` factor adjusts gains based on whether the board is accelerating or braking (see brake scaling below).

---

## The Three Terms

### P — Proportional Term
`P = kp * error`

Produces force proportional to how far the board is from the setpoint. If the nose is 5° too low, P pushes harder than if it's only 2° too low. This is the primary restoring force.

**Too low:** Board feels loose, wallowy. Large errors are not strongly corrected.
**Too high:** Board oscillates — overcorrects, which causes an error in the opposite direction, which overcorrects again.

### I — Integral Term
`I += ki * error * dt` (clamped to ±`ki_limit`)

Accumulates error over time. Corrects for persistent lean that P alone doesn't fully eliminate — for example, if the rider consistently stands slightly forward, P will hold an error at steady state (it only produces zero output when error is zero). The I term winds up and adds bias to zero out that steady-state error.

**`ki_limit`** prevents unbounded wind-up. On a long uphill, the I term would keep growing without this limit, then produce an unwanted forward push when the hill ends.

**Too low:** Persistent forward/backward lean at cruising speed.
**Too high:** "Hunting" — the board over-corrects drift and oscillates slowly.

### rate_P — Rate-Proportional Term (Derivative)
`rate_P = kp2 * (-pitch_rate)`

Damps pitch velocity. If the nose is moving downward rapidly (negative pitch rate), `rate_P` produces a corrective force before the error gets large. This is the "D" term in traditional PID, but implemented as pitch rate gain rather than angle derivative — it reads directly from the gyroscope.

The negative sign: a downward-moving nose has a negative pitch rate; the correction should push it back up (positive current), so `rate_P = -kp2 * (negative) = positive`. Correct direction.

**Too low:** Board feels snappy and unstable — it responds to errors after they grow, not as they're developing.
**Too high:** Over-damped. Board feels dead or sluggish. PID spends too much energy fighting its own corrections.

---

## Brake Scaling

During deceleration, the effective gains are multiplied:

```c
effective_kp  = kp  * kp_brake_scale.ema    // kp_brake_scale approaches kp_brake
effective_kp2 = kp2 * kp2_brake_scale.ema   // kp2_brake_scale approaches kp2_brake
```

The scale transitions via a 1 Hz EMA between `1.0` (accelerating) and the configured `kp_brake` / `kp2_brake` (braking). This transition takes ~1 second to complete.

**Why reduce gains while braking?** Braking dynamics are different — the motor is regenerating, the angular response is different, and aggressive gains can cause resonance. Many riders run `kp_brake = 0.7–0.85` for a slightly softer braking feel.

Setting both to `1.0` eliminates any difference between acceleration and braking PID feel.

---

## Softstart

On engagement, the motor current is clamped by `softstart_pid_limit`, which ramps from 0 to `current_max` at 100 A/s:

```c
softstart_pid_limit += 100.0 * dt;
new_current = clamp(pid_output + booster, -softstart_pid_limit, softstart_pid_limit);
```

This prevents the motor from jerking at engagement even if the board is at a large angle error. The ramp takes about 0.5 seconds to reach full current.

---

## Output Clamping

```c
new_current = clamp(output, motor.current_min, motor.current_max)
```

`current_min` and `current_max` are read from `mc_configuration.l_current_min/max` (the BLDC motor limits). These are the absolute ceiling — no matter how large the PID output, the motor will never receive more than these limits.

---

## `PID` Struct

```c
// pid.h:25–35
PID {
    float p;           // Current P term value
    float i;           // Current I term value
    float rate_p;      // Current rate-P term value
    EMA p_fwd_scale;   // Scale EMA when moving forward
    EMA p_bwd_scale;   // Scale EMA when moving backward
    EMA rate_p_fwd_scale;
    EMA rate_p_bwd_scale;
}
```

---

## References

- [[pid.c]] — `pid_control()` lines 51–89, full control law
- [[pid.h]] — `PID` struct lines 25–35
- [[main.c]] — `pid_control()` called in `imu_ref_callback()` lines 724–763
- [[setpoint-composition|Setpoint Composition]] — produces the `setpoint` that PID error is computed against
- [[Booster]] — adds current to PID output for large-angle stabilization
- [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] — source of `balance_pitch` and `pitch_rate`
- [[refloat-config|RefloatConfig]] — `kp`, `ki`, `kp2`, `ki_limit`, `kp_brake`, `kp2_brake`
- [[tuning-pid|Tuning the PID Controller]] — symptom-based tuning guide
