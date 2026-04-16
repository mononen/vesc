---
title: "How to Tune Your Onewheel"
aliases:
  - "How to Tune Your Onewheel"
tags:
  - index
  - tuning
  - navigation
date: 2026-04-16
source_files: []
---

# How to Tune Your Onewheel

A guided entry point for tuning Refloat. Follow the order below — each layer builds on the previous one.

---

## Tuning Philosophy

Every parameter in Refloat ultimately moves one of two things:
1. **The setpoint** — the angle the board is trying to hold (ride-feel algorithms, tiltbacks)
2. **The PID gains** — how aggressively the board corrects toward the setpoint

The PID is the foundation. If the PID is poorly tuned, the ride-feel algorithms on top of it will feel broken too — they're just adjusting a target that an unstable controller can't track accurately.

**Tune in this order:**
1. PID baseline
2. Mahony filter (if needed)
3. ATR (terrain feel)
4. TorqueTilt, BrakeTilt, TurnTilt (character)
5. Booster (limit behavior)
6. Tiltbacks and speed limits
7. Engagement and fault thresholds

---

## 1. Start with PID

[[tuning-pid|Tuning the PID Controller]] covers the core `kp`, `ki`, `kp2` parameters with a symptom table:

| Symptom | Fix |
|---------|-----|
| Loose / wallowy | Raise `kp` |
| Oscillates / buzzes | Raise `kp2` or lower `kp` |
| Leans forward at speed | Raise `ki` |
| Nosedives on braking | Raise `kp_brake` |
| Twitchy on rough pavement | Lower `kp` or lower `mahony_kp` |

Get the board stable and predictable before touching anything else.

---

## 2. Mahony Filter (if PID feels stuck)

If raising `kp` always causes buzzing, or the board feels oddly delayed, the [[mahony-ahrs-filter|Mahony AHRS Filter]] may be the issue.

[[tuning-mahony|Tuning the Mahony Filter]] explains:
- High `mahony_kp` → fast but noisy angle estimate → buzz with high `kp`
- Low `mahony_kp` → smooth but lagging estimate → need higher `kp` to compensate

Adjust `mahony_kp`, then re-verify your PID settings.

---

## 3. ATR — Terrain Adaptation

[[tuning-atr|Tuning ATR]] covers the most impactful ride-feel feature. With good ATR:
- Hills feel like flat ground (board compensates automatically)
- Downhills don't feel runaway-ish
- Rough terrain is absorbed

Key parameters: `atr_strength_up`, `atr_strength_down`, `atr_threshold_up/down`, `atr_amps_accel_ratio` (calibration).

**Important first step:** Calibrate `atr_amps_accel_ratio` on flat ground so `atr.accel_diff` hovers near zero at steady cruise speed.

---

## 4. Ride Feel Character

These four algorithms (covered in [[tuning-ride-feel|Tuning Ride Feel]]) add personality:

**[[torque-tilt|Torque Tilt]]** — Makes acceleration and braking feel alive. The nose rises with current.
- First sign it's working: nose noticeably rises during hard acceleration

**[[brake-tilt|Brake Tilt]]** — Makes deceleration feel natural. Nose lifts slightly during braking.
- Tune `braketilt_strength` until braking feels intuitive, not jarring

**[[turn-tilt|Turn Tilt]]** — Prevents corner nosedive. Nose holds steady in carves.
- Tune on smooth pavement, raising `turntilt_strength` until cornering feels planted

**[[Booster]]** — Stiffens the board at the limits. Normal riding feels unchanged; large lean angles feel firm.
- Add last; only needed if the board still "gives up" at extreme angles

---

## 5. Speed Limits and Tiltbacks

[[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] covers all the graduated speed warnings:

- **[[nose-angling|Nose Angling and Pushback Speed Control]]** — gradual nose-rise with speed (cruise control feel)
- **Duty tiltback** — urgent pushback when motor duty is high
- **Speed tiltback** — same but for downhill speed
- **HV/LV tiltbacks** — battery protection

Ensure the tiltback angles are firm enough to feel, but not so aggressive they throw you off.

---

## 6. Engagement and Fault Thresholds

[[tuning-engagement|Tuning Engagement and Startup]] covers:

- `startup_pitch_tolerance` — how level the board must be to engage
- `fault_adc1/2` — footpad sensitivity calibration
- `fault_delay_*` — how long faults must persist before stopping
- `enable_quickstop` — clean deliberate dismounts

This is about reliability and safety, not ride feel.

---

## Reference Sheets

- [[refloat-config|RefloatConfig]] — complete annotated parameter list
- [[bldc-mc-configuration]] — motor current limits and temperature protection

---

## Navigation

- [[vault-home|Vault Home]] — top-level index
- [[how-my-board-stays-upright|How My Board Stays Upright]] — understand the control loop before tuning it
