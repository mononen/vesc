---
title: "Tuning the Mahony Filter"
aliases:
  - "Tuning the Mahony Filter"
tags:
  - tuning
  - mahony
  - ahrs
  - sensor
  - practical
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/balance_filter.c
  - refloat/src/balance_filter.h
  - refloat/src/conf/datatypes.h
---

# Tuning the Mahony Filter

The [[mahony-ahrs-filter|Mahony AHRS Filter]] sits upstream of everything else — it produces the `balance_pitch` angle estimate that the [[pid-controller|PID Controller]] acts on. Getting its gain (`mahony_kp`) right is often the difference between a smooth, stable ride and unexplained buzzing or sluggishness.

Most riders never touch this and use whatever the defaults are. But if your PID tuning feels stuck — if raising `kp` always causes buzzing or the board feels oddly delayed — the Mahony KP is where to look.

---

## What `mahony_kp` Controls

The Mahony filter fuses two sensors:
- **Gyroscope:** Fast, accurate rate data, but drifts over time
- **Accelerometer:** Stable long-term reference for gravity direction, but noisy and disturbed by acceleration

`mahony_kp` controls how strongly the accelerometer pulls the estimate toward its reading. 

- **High `mahony_kp`** — Accelerometer dominates. The angle estimate tracks gravity quickly but is noisier (the accelerometer is disturbed by every bump and motor current pulse). The estimate reacts fast but can jitter.
- **Low `mahony_kp`** — Gyroscope dominates. The angle estimate is smooth but drifts slowly and lags behind sudden changes in actual angle. The estimate is clean but slow.

---

## Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `mahony_kp` | 0.1–0.5 | Accelerometer feedback gain for pitch estimation |
| `mahony_kp_roll` | 0.1–0.5 | Same but for roll axis |

Both have the same fundamental tradeoff. Roll is generally less critical for balance (the board balances on the pitch axis), so `mahony_kp_roll` can usually match `mahony_kp` without much consequence.

---

## Symptom-Based Tuning

### Board buzzes even with low `kp`

**Cause:** `mahony_kp` is too high. The angle estimate is noisy — every small vibration from the motor or road is being seen by the PID as a rapid pitch change. The PID's P term and especially `kp2` (pitch rate damping) are amplifying this noise into oscillation.

**Fix:** Lower `mahony_kp` in steps of 0.05. A value of 0.15–0.20 is smooth. You may find that after lowering it, you can raise `kp` without buzzing returning — which overall improves feel.

**How to tell:** If the buzz disappears on very smooth pavement but returns on rough pavement, it's noise-driven → Mahony KP is the likely cause.

---

### Board feels like it reacts to lean with a delay

**Cause:** `mahony_kp` is too low, or the IMU sample rate is lower than expected. The angle estimate is lagging behind the actual board movement.

**Symptom feels like:** You lean forward, the board hesitates for 50–100ms before pushing back. This is different from soft `kp` — the spring feels slow to engage, not weak.

**Fix:** Raise `mahony_kp` toward 0.35–0.4. Also verify `hertz` (the main loop frequency) is at its configured value by checking telemetry's `main_frequency`. A loop running slower than expected will also introduce lag.

---

### Board feels great on smooth pavement but chattery on rough terrain

**Cause:** On rough terrain, the accelerometer is constantly excited by impacts, and `mahony_kp` is high enough that these impacts show up in `balance_pitch`. The PID sees rapid-fire pitch transients and fights them.

**Fix:** Lower `mahony_kp`. The gyroscope handles high-frequency events well (it's measuring angular rate, not linear acceleration) — reducing Mahony KP lets the gyro carry more of the burden during impacts.

**Secondary fix:** Reduce `kp2` slightly. The pitch-rate derivative term is what translates rapid angle changes into motor response. Lower `kp2` means less response to fast transients.

---

### Angle estimate drifts noticeably while stationary

**Cause:** `mahony_kp` is very low and gyroscope drift is accumulating. This is generally not a problem during riding (the accelerometer correction still runs) but can appear when the board is left stationary for extended periods.

**Note:** If the drift is very large and rapid, check for gyroscope calibration offsets — this is an IMU calibration issue, not a `mahony_kp` issue. Refloat relies on BLDC's IMU calibration (`gyro_offsets[3]` in [[bldc-mc-configuration]]).

---

## The Accelerometer Confidence Mechanism

Refloat's Mahony implementation includes a feature that automatically reduces the accelerometer's influence during high-G events (hard acceleration, braking, impacts). This is `calculate_acc_confidence()` in [[balance_filter.c]].

When the accelerometer vector magnitude deviates significantly from 1G, the confidence weight drops toward zero. This means the filter trusts the gyroscope more during the dynamic events where the accelerometer is least reliable.

**Practical implication:** Your `mahony_kp` setting is effectively the *maximum* accelerometer influence. During hard acceleration, confidence drops and the effective influence is lower. This is why the filter handles acceleration-induced angle errors better than a naive Mahony implementation.

You do not tune this directly. It runs automatically.

---

## `mahony_kp_roll` — When It Matters

Roll stability matters for two cases:
1. **Turn Tilt** — uses the roll angle to detect turning; a noisy roll estimate produces false TurnTilt activation
2. **Darkride mode** — uses roll to detect board-upside-down (> 150°)

For most riding, `mahony_kp_roll` can equal `mahony_kp`. If you're getting unexpected [[turn-tilt|Turn Tilt]] triggers on rough roads, try lowering `mahony_kp_roll` slightly — this smooths the roll estimate and reduces spurious yaw-from-roll events.

---

## Interaction with `kp2`

There is a fundamental coupling between `mahony_kp` and `kp2`:

- The `kp2` (rate-P) term uses `pitch_rate` — the angular velocity of the board
- `pitch_rate` is derived from the IMU gyro Y axis directly, **not** from the Mahony angle derivative
- The Mahony angle estimate is only used for the `pitch` (and thus `error`) calculation

This means `kp2` is relatively insulated from Mahony KP noise, but `kp`'s P term is fully exposed to it. When Mahony KP is high:
- `kp` sees noisy angle → noisy P term → needs lower `kp` to avoid buzz
- `kp2` sees clean gyro rate → still works well

When Mahony KP is low:
- `kp` sees smooth angle but lags → needs higher `kp` to compensate stiffness
- `kp2` unchanged → same clean rate derivative

**Design implication:** Low Mahony KP naturally pushes you toward higher `kp` (to compensate for sluggish angle estimate) and potentially lower `kp2` (since the already-smooth angle means oscillation is less likely with high `kp`). High Mahony KP pushes you toward lower `kp` and higher `kp2`. These are two legitimate design points with different feels.

---

## Suggested Starting Points

**Smooth pavement, stable feel:**
```
mahony_kp = 0.20
mahony_kp_roll = 0.20
```

**Technical terrain, faster response:**
```
mahony_kp = 0.30
mahony_kp_roll = 0.25
```

After changing `mahony_kp`, you will likely need to re-verify `kp` and `kp2` — the system behaves differently with different filter dynamics.

---

## References

- [[balance_filter.c]] — `balance_filter_update()`, Mahony algorithm, lines 73–134; `calculate_acc_confidence()` for confidence weighting
- [[balance_filter.h]] — `BalanceFilterData` struct: `q0–q3`, `kp_pitch`, `kp_roll`, `kp_yaw`, `acc_mag`
- [[refloat-config|RefloatConfig]] — `mahony_kp`, `mahony_kp_roll` in `datatypes.h:208–312`
- [[imu-pitch-roll-yaw]] — how `balance_pitch` and `pitch_rate` are extracted from filter output
- [[pid-controller|PID Controller]] — consumes `balance_pitch` and `pitch_rate`; explain how Mahony KP affects each term
- [[tuning-pid|Tuning the PID Controller]] — PID tuning guidance that depends on Mahony KP setting
