---
title: "Mahony AHRS Filter"
aliases:
  - "Mahony AHRS Filter"
  - "Mahony Filter"
  - "Mahony AHRS"
tags:
  - sensor
  - ahrs
  - mahony
  - quaternion
  - imu
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/balance_filter.c
  - refloat/src/balance_filter.h
  - bldc/imu/ahrs.c
---

# Mahony AHRS Filter

The Mahony AHRS (Attitude and Heading Reference System) filter is the foundation of Refloat's balance sensing. It takes raw gyroscope and accelerometer readings and produces a stable, low-latency estimate of the board's orientation as a quaternion — from which pitch, roll, and yaw angles are extracted.

---

## The Sensor Fusion Problem

The board has two sources of orientation information, each with opposing weaknesses:

**Gyroscope** — measures angular rate (degrees/second)
- Very fast, accurate on short timescales
- Drifts: integrating rate over time accumulates error — after a few minutes without correction, the estimated angle drifts away from true angle
- Not disturbed by linear acceleration

**Accelerometer** — measures specific force (acceleration including gravity)
- Long-term stable: always points toward gravity when stationary
- Noisy: disturbed by every bump, motor vibration, and acceleration/braking event
- Cannot be trusted during dynamic motion

The Mahony filter fuses both: the gyro provides fast, accurate angle tracking; the accelerometer provides a slow, stable correction to prevent drift.

---

## The Algorithm

Implemented in [[balance_filter.c]] (Refloat's version) and [[bldc/imu/ahrs.c]] (bldc's version — same algorithm, separate instance).

**Step 1 — Normalize accelerometer vector:**
```
acc_normalized = acc / |acc|
```
This gives a unit vector pointing toward gravity (approximately, when not accelerating).

**Step 2 — Estimate gravity from current quaternion:**
```
v = rotate(quaternion, [0, 0, 1])   // What does "down" look like in body frame?
```

**Step 3 — Compute correction error (cross product):**
```
error = cross(acc_normalized, v)    // Perpendicular error between measured and estimated gravity
```
The cross product magnitude is the sine of the angle between the accelerometer's gravity estimate and the filter's current gravity estimate.

**Step 4 — Apply proportional feedback to gyro:**
```
gyro_corrected = gyro + kp * error + ki * integral(error)
```
The correction nudges the gyro integration toward where the accelerometer says gravity is.

**Step 5 — Integrate corrected gyro rate into quaternion:**
```
q += 0.5 * q ⊗ [0, ωx, ωy, ωz] * dt
q = q / |q|    // Renormalize
```

---

## Accelerometer Confidence

A key feature in Refloat's implementation: `calculate_acc_confidence()` in [[balance_filter.c]].

During hard acceleration or braking, the accelerometer reads more than 1G (or less, on regen). The filter detects this by checking how far the accelerometer magnitude deviates from 1G:

```
error_from_1g = |acc_magnitude - 1.0|
confidence = 1.0 - clamp(error_from_1g / max_error, 0, 1)
```

The effective `kp` used in step 4 is multiplied by this confidence:
```
effective_kp = mahony_kp * confidence
```

When the board is accelerating hard (e.g., 1.5G), confidence drops toward 0 and the filter relies almost entirely on the gyroscope. When stationary or at constant speed, confidence is near 1.0 and the accelerometer correction is at full strength. This prevents the filter from being thrown off by dynamic maneuvers.

---

## Two Instances Running in Parallel

Both Refloat and bldc run their own Mahony filter:

| Filter | Where | Used For |
|--------|-------|----------|
| Refloat's | `balance_filter.c`, runs in `imu_ref_callback` | `balance_pitch` → PID input (the real balance signal) |
| bldc's | `bldc/imu/ahrs.c`, runs in bldc's IMU ISR | `VESC_IF->imu_get_pitch()` → secondary telemetry |

Refloat does not use bldc's pitch estimate for control — it runs its own filter so it has full control over filter parameters (`mahony_kp`, `mahony_kp_roll`) without depending on bldc's IMU configuration.

---

## Quaternion to Euler Angles

After the filter update, the quaternion [q0, q1, q2, q3] is converted to Euler angles in [[imu.c]]:

```
pitch = atan2(2*(q0*q1 + q2*q3), 1 - 2*(q1² + q2²))
roll  = asin(2*(q0*q2 - q3*q1))
yaw   = atan2(2*(q0*q3 + q1*q2), 1 - 2*(q2² + q3²))
```

These are the `imu.pitch`, `imu.roll`, `imu.yaw` values. An additional offset (`flywheel_pitch_offset`) is applied in flywheel mode.

---

## Effect on Ride Feel

`mahony_kp` is the primary tuning parameter. See [[tuning-mahony|Tuning the Mahony Filter]] for the full symptom-based guide. Key tradeoffs:

- **Higher `mahony_kp`:** Faster response to actual angle changes, more noise from accelerometer
- **Lower `mahony_kp`:** Smoother angle estimate, slower to track real angle changes, gyro drift correction less aggressive

---

## References

- [[balance_filter.c]] — full Mahony implementation: `balance_filter_update()` lines 73–134, `calculate_acc_confidence()`
- [[balance_filter.h]] — `BalanceFilterData` struct: `q0–q3`, `kp_pitch`, `kp_roll`, `kp_yaw`, `acc_mag`
- [[bldc/imu/ahrs.c]] — bldc's equivalent Mahony implementation, `ahrs_update_mahony_imu()` line 97
- [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] — angle extraction from the quaternion output
- [[refloat-config|RefloatConfig]] — `mahony_kp`, `mahony_kp_roll` at `datatypes.h:208`
- [[tuning-mahony|Tuning the Mahony Filter]] — how to set `mahony_kp` based on symptoms
- [[pid-controller|PID Controller]] — consumes `balance_pitch` produced by this filter
