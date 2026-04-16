---
title: "How My Board Stays Upright"
aliases:
  - "How My Board Stays Upright"
tags:
  - index
  - narrative
  - balance
  - overview
date: 2026-04-16
source_files: []
---

# How My Board Stays Upright

A guided narrative from sensor input to wheel torque — the complete control loop explained in plain language, with links to deeper notes at each step.

---

## The Problem

A onewheel is an inverted pendulum. Left alone, it falls over. Keeping it upright requires continuous, fast corrections — the wheel must accelerate under the rider's center of gravity faster than the board can fall.

The board executes this correction about 20,000 times per second.

---

## Step 1: Sensing the Angle

The IMU (Inertial Measurement Unit) chip on the board contains:
- A **gyroscope** — measures how fast the board is rotating (degrees/second)
- An **accelerometer** — measures which direction gravity is pulling

Neither alone is sufficient. The gyroscope drifts over time. The accelerometer is disturbed by acceleration and vibration.

The [[mahony-ahrs-filter|Mahony AHRS Filter]] fuses both sensors into a stable, fast angle estimate. It does this by using the gyroscope as the primary source (fast, accurate short-term) and the accelerometer as a slow correction (stable long-term, unreliable short-term). The result is a quaternion — a compact mathematical representation of the board's full 3D orientation — updated every ~50 µs.

From that quaternion, [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] extracts:
- **Pitch** — nose-up or nose-down angle
- **Pitch rate** — how fast the nose is moving

---

## Step 2: Computing the Error

The board has a target angle — the `setpoint`. At normal riding speed, this is approximately 0° (level). If the rider leans forward, the nose pitches down, and the error (setpoint − pitch) becomes positive.

```
error = setpoint - balance_pitch
```

The setpoint isn't always 0. It's continuously updated by a layer of ride-feel algorithms — tilted slightly for hills (ATR), for acceleration (TorqueTilt), for turns (TurnTilt), and for safety warnings (tiltbacks). See [[setpoint-composition|Setpoint Composition]] for how all those contributions combine.

---

## Step 3: The PID Controller Decides How Hard to Push

The [[pid-controller|PID Controller]] converts the error into a motor current command using three terms:

**P (Proportional):** `kp × error`
More tilted = more push. Simple, proportional response.

**I (Integral):** Accumulates error over time.
Corrects for persistent lean (e.g., always slightly forward at cruising speed).

**rate_P (Derivative-like):** `kp2 × (-pitch_rate)`
Resists the *rate* of tilting. If the nose is falling fast, this pushes back hard before the angle gets large. Provides stability.

The sum `P + I + rate_P` is the target motor current in amps.

---

## Step 4: Sending the Command to the Motor

The PID output is sent to the BLDC firmware via the [[refloat-bldc-interface|Refloat–BLDC Interface]]:

```c
VESC_IF->mc_set_current(balance_current);
```

This sets a target torque current (`Iq`) that the motor must produce.

---

## Step 5: Field-Oriented Control Executes the Command

The VESC motor controller runs [[foc-overview|FOC Overview]] at 20 kHz. Its job is to actually deliver the requested current to the motor, despite the motor spinning at varying speeds and the back-EMF changing moment to moment.

FOC does this by:
1. **[[clarke-park-transforms|Clarke and Park Transforms]]** — Converting three-phase AC motor currents into a rotating reference frame where they look like DC values (`id` and `iq`)
2. **[[current-pi-loop|Current PI Loop]]** — PI controllers drive `iq` toward the commanded value using voltage adjustments
3. **[[space-vector-modulation|Space Vector Modulation]]** — Converting the voltage commands back into three PWM duty cycles
4. **PWM timers** — The actual voltage applied to motor windings, switching at 20 kHz

---

## Step 6: Motor Produces Torque → Wheel Accelerates → Board Tilts Back

The motor current creates magnetic torque that accelerates the wheel. If the nose was pitching forward, accelerating the wheel forward creates an inertial reaction that pushes the nose back up. Newton's third law in action.

The whole cycle repeats: the board pitches, the sensor reads it, the filter estimates the angle, the PID computes a correction, the motor executes it, the board responds. 20,000 times per second.

---

## The Stack in One Diagram

```
  Gyro + Accel
       │
       ▼
  Mahony Filter (balance_filter.c)
       │ balance_pitch, pitch_rate
       ▼
  PID Controller (pid.c)
       │ balance_current (amps)
       ▼
  Booster addition
       ▼
  mc_set_current()           ← Refloat → bldc boundary
       │
       ▼
  Clarke Transform            (mcpwm_foc.c)
       │ (i_alpha, i_beta)
       ▼
  Park Transform
       │ (id, iq)
       ▼
  Current PI Controllers
       │ (vd, vq)
       ▼
  Inverse Park
       │ (v_alpha, v_beta)
       ▼
  Space Vector Modulation
       │ (duty_A, duty_B, duty_C)
       ▼
  PWM Timers → Motor Phases → Torque → Wheel → Board tilts back
```

---

## Where to Go Next

- [[data-flow|Data Flow: From Sensor to PWM]] — the same story with exact variable names, code locations, and latency numbers
- [[setpoint-composition|Setpoint Composition]] — how ride-feel algorithms affect the target angle
- [[system-overview|System Overview]] — the two-codebase architecture (Refloat + bldc)
- [[thread-model|Thread Model and Timing]] — why certain things run at 20 kHz and others at 1 kHz
