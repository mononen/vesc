---
title: "Vault Home"
aliases:
  - "Vault Home"
tags:
  - index
  - hub
  - navigation
date: 2026-04-16
source_files: []
---
# VESC Onewheel Documentation

This vault covers the Refloat self-balancing controller package and the BLDC firmware it runs on. The goal is to understand the full stack: from how the IMU detects lean angles, through the control algorithms that decide motor current, to the power electronics that make the wheel spin.

---

## The Two Codebases

| | [[system-overview|Refloat]] | [[system-overview|BLDC]] |
|---|------------|------|
| **Role** | Balance controller | Motor firmware |
| **Language** | C (VESC package) | C (STM32 firmware) |
| **Runs on** | Inside bldc as a plugin | STM32F4 microcontroller |
| **Key files** | `src/main.c`, `src/conf/datatypes.h` | `motor/mcpwm_foc.c`, `datatypes.h` |
| **Repo** | `refloat/` | `bldc/` |

They communicate through the [[refloat-bldc-interface|Refloat–BLDC Interface]] (`vesc_c_if` function pointer table).

---

## Start Here

### "How does the board stay upright?"
→ [[how-my-board-stays-upright|How My Board Stays Upright]] — narrative walkthrough of the full control loop

### "How do I tune it?"
→ [[how-to-tune|How to Tune Your Onewheel]] — ordered tuning guide from PID to tiltbacks

### "How does the motor actually work?"
→ [[foc-overview|FOC Overview]] → [[clarke-park-transforms|Clarke and Park Transforms]] → [[current-pi-loop|Current PI Loop]] → [[space-vector-modulation|Space Vector Modulation]]

### "What happens when I crash / step off?"
→ [[state-machine|State Machine]] → [[fault-detection|Fault Detection]] → [[footpad-sensor|Footpad Sensor]]

---

## All Notes by Topic

### Architecture
- [[system-overview|System Overview]] — Refloat + bldc two-codebase model, two control loops
- [[thread-model|Thread Model and Timing]] — ChibiOS threads, 1 kHz vs 20 kHz
- [[refloat-bldc-interface|Refloat–BLDC Interface]] — `vesc_c_if` API in detail
- [[data-flow|Data Flow: From Sensor to PWM]] — end-to-end trace of one control cycle

### Sensors
- [[mahony-ahrs-filter|Mahony AHRS Filter]] — quaternion filter fusing gyro + accel
- [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] — angle extraction, balance_pitch vs pitch, pitch_rate
- [[footpad-sensor|Footpad Sensor]] — ADC states, engagement gating, fault delays

### Balance Control
- [[pid-controller|PID Controller]] — P, I, rate-P terms; brake scaling; softstart
- [[setpoint-composition|Setpoint Composition]] — full setpoint formula; ATR vs TorqueTilt arbitration
- [[Booster]] — nonlinear current injection at large lean angles
- [[traction-control|Traction Control and Wheelslip]] — wheelslip detection and freewheel response

### Ride Feel
- [[atr|ATR — Adaptive Terrain Response]] — accel_diff model, terrain adaptation
- [[torque-tilt|Torque Tilt]] — nose rise proportional to motor current
- [[brake-tilt|Brake Tilt]] — nose lift during braking, downhill damping
- [[turn-tilt|Turn Tilt]] — yaw-rate-based corner compensation
- [[nose-angling|Nose Angling and Pushback Speed Control]] — variable/constant speed-based nose angle

### Safety
- [[state-machine|State Machine]] — RunState, Mode, SAT, StopCondition, all transitions
- [[fault-detection|Fault Detection]] — pitch/roll/switch faults, delays, quickstop
- [[pushback-tiltback|Pushback and Tiltback System]] — SAT hierarchy, duty/speed/HV/LV/temp tiltbacks

### Motor / FOC Layer
- [[foc-overview|FOC Overview]] — why FOC, Id/Iq, 20 kHz ISR
- [[clarke-park-transforms|Clarke and Park Transforms]] — 3-phase → rotating frame mathematics
- [[current-pi-loop|Current PI Loop]] — Id/Iq PI controllers, decoupling feedforward
- [[space-vector-modulation|Space Vector Modulation]] — voltage vector → PWM duty cycles
- [[motor-data|Motor Data and Telemetry]] — ERPM, filt_current, acceleration, braking flag

### Configuration Reference
- [[refloat-config|RefloatConfig]] — all Refloat parameters annotated
- [[bldc-mc-configuration]] — motor current limits, FOC parameters, temperature limits

### Tuning Guides
- [[tuning-pid|Tuning the PID Controller]] — kp/ki/kp2 symptom table
- [[tuning-mahony|Tuning the Mahony Filter]] — filter dynamics and noise tradeoffs
- [[tuning-atr|Tuning ATR]] — terrain response calibration and symptom fixes
- [[tuning-ride-feel|Tuning Ride Feel]] — character tuning
- [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] — speed limit configuration
- [[tuning-engagement|Tuning Engagement and Startup]] — footpad thresholds, fault delays, startup tolerances

---

## Version Info

| Repo | Branch | Version |
|------|--------|---------|
| bldc | master | v6.00-1258 (SHA: 00b60c89) |
| refloat | main | v1.2.2-beta1-36 (SHA: 5b399843) |

*(From `state.md` — verify with `git log` for current state)*
