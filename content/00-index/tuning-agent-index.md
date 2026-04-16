---
title: "Tuning Agent Index"
aliases:
  - "Tuning Agent Index"
tags:
  - index
  - tuning
  - agent
  - navigation
date: 2026-04-16
source_files: []
---

# Tuning Agent Index

This file is a navigation guide for an AI agent helping diagnose or suggest Refloat tuning changes. Use it to locate the right notes for a given symptom, parameter, or subsystem — then read those notes for the full context before making suggestions.

---

## How to Use This Index

1. **Identify the symptom or parameter** the user is asking about
2. **Find the relevant section** below and read the linked notes
3. **Look up the exact C field name, default, and range** in [[parameter-map|Parameter Map: Code ↔ VESC Tool]] — use this whenever translating between a UI label and a code variable
4. **Look at the source file** listed in each note's frontmatter to verify current behavior
5. **Suggest one change at a time** — these parameters interact; changing multiple at once makes it hard to isolate cause

> All parameter names used in this index are **C struct field names** from `RefloatConfig` (e.g. `kp`, `atr_strength_up`). Cross-reference with [[parameter-map|Parameter Map]] to find the corresponding VESC Tool UI label.

---

## Tuning Order (Start Here If Starting From Scratch)

Always tune in this sequence. Later layers depend on earlier ones being stable.

| Step | What | Note |
|------|------|------|
| 1 | Core balance feel | [[tuning-pid|Tuning the PID Controller]] |
| 2 | Sensor noise / filter lag | [[tuning-mahony|Tuning the Mahony Filter]] |
| 3 | Hills and terrain | [[tuning-atr|Tuning ATR]] |
| 4 | Acceleration/braking feel | [[tuning-ride-feel|Tuning Ride Feel]] |
| 5 | Speed limits and safety tilts | [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] |
| 6 | Startup, footpad, engagement | [[tuning-engagement|Tuning Engagement and Startup]] |

---

## Symptom → Note Map

### Board feels unstable or oscillates

| Symptom | Most likely cause | Read |
|---------|-------------------|------|
| Buzzing / high-freq oscillation at speed | `kp` too high | [[tuning-pid|Tuning the PID Controller]] |
| Slow wobble / rocking | `kp2` too low (underdamped) | [[tuning-pid|Tuning the PID Controller]] |
| Twitchy on rough pavement | `mahony_kp` too high (noisy pitch) | [[tuning-mahony|Tuning the Mahony Filter]] |
| Oscillation that only ATR makes worse | `atr_on_speed` too high or `atr_filter` too low | [[tuning-atr|Tuning ATR]] |
| Surging feel on hills | ATR overshoot — lower `atr_on_speed`, raise `atr_filter` | [[tuning-atr|Tuning ATR]] |

### Board leans or drifts

| Symptom | Most likely cause | Read |
|---------|-------------------|------|
| Leans forward at constant speed | `ki` too low (integral not correcting) | [[tuning-pid|Tuning the PID Controller]] |
| ATR adds constant tilt on flat ground | `atr_amps_accel_ratio` miscalibrated | [[tuning-atr|Tuning ATR]] |
| Pitch reads wrong at rest | `mahony_kp`/`mahony_ki` drift | [[tuning-mahony|Tuning the Mahony Filter]] |
| Board tilts noticeably on turns | TurnTilt too strong | [[tuning-ride-feel|Tuning Ride Feel]] |

### Hills and terrain feel wrong

| Symptom | Most likely cause | Read |
|---------|-------------------|------|
| Board doesn't respond to hills | `atr_strength_up/down` too low or threshold too high | [[tuning-atr|Tuning ATR]] |
| Downhills feel uncontrolled | `atr_strength_down` too low | [[tuning-atr|Tuning ATR]] |
| ATR too aggressive at speed | `atr_speed_boost` too high | [[tuning-atr|Tuning ATR]] |
| ATR slow to respond on steep terrain | `atr_on_speed` too low | [[tuning-atr|Tuning ATR]] |

### Acceleration / braking feel wrong

| Symptom | Most likely cause | Read |
|---------|-------------------|------|
| Nose lifts too much under hard acceleration | TorqueTilt `torquetilt_strength` too high | [[tuning-ride-feel|Tuning Ride Feel]] |
| Regen braking feels harsh | BrakeTilt `braketilt_strength` too high | [[tuning-ride-feel|Tuning Ride Feel]] |
| Board doesn't push back on braking | BrakeTilt too low | [[tuning-ride-feel|Tuning Ride Feel]] |
| Nosedive on hard braking | `kp_brake` or `kp2_brake` too low | [[tuning-pid|Tuning the PID Controller]] |
| Wheelspin / motor stutters | Traction control threshold | [[traction-control|Traction Control and Wheelslip]] |

### Speed and safety feel wrong

| Symptom | Most likely cause | Read |
|---------|-------------------|------|
| Pushback starts too early or too late | `tiltback_*_speed` or `tiltback_*_erpm` | [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] |
| Pushback is too subtle (ignored) | `tiltback_*_angle` too low | [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] |
| Duty-cycle cutout feels sudden | `tiltback_duty` threshold or angle | [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] |
| Nose angling on pushback feels wrong | `noseangling_*` parameters | [[nose-angling|Nose Angling and Pushback Speed Control]] |
| Low/high voltage tiltback too aggressive | `lv_*` / `hv_*` thresholds | [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] |

### Startup and engagement feel wrong

| Symptom | Most likely cause | Read |
|---------|-------------------|------|
| Board is hard to engage | `startup_*` thresholds too tight | [[tuning-engagement|Tuning Engagement and Startup]] |
| Board disengages unexpectedly | Footpad sensitivity or fault thresholds | [[tuning-engagement|Tuning Engagement and Startup]] |
| False faults | IMU noise, footpad wiring, or fault timeouts | [[fault-detection|Fault Detection]] |

---

## Parameter → Note Map

Use this when the user asks about a specific parameter by name. All names are **C field names** from `RefloatConfig`. For the matching VESC Tool UI label, default value, and valid range, see [[parameter-map|Parameter Map: Code ↔ VESC Tool]].

| C field(s) | Subsystem | Read |
|------------|-----------|------|
| `kp`, `ki`, `ki_limit`, `kp2`, `kp_brake`, `kp2_brake`, `brake_current` | PID balance | [[tuning-pid|Tuning the PID Controller]], [[pid-controller|PID Controller]] |
| `mahony_kp`, `mahony_kp_roll`, `hertz` | IMU filter | [[tuning-mahony|Tuning the Mahony Filter]], [[mahony-ahrs-filter|Mahony AHRS Filter]] |
| `atr_strength_up`, `atr_strength_down`, `atr_threshold_up`, `atr_threshold_down`, `atr_speed_boost`, `atr_angle_limit`, `atr_on_speed`, `atr_off_speed`, `atr_response_boost`, `atr_transition_boost`, `atr_filter`, `atr_amps_accel_ratio`, `atr_amps_decel_ratio` | Terrain response | [[tuning-atr|Tuning ATR]], [[atr|ATR — Adaptive Terrain Response]] |
| `torquetilt_start_current`, `torquetilt_angle_limit`, `torquetilt_on_speed`, `torquetilt_off_speed`, `torquetilt_strength`, `torquetilt_strength_regen` | Accel/decel feel | [[tuning-ride-feel|Tuning Ride Feel]], [[torque-tilt|Torque Tilt]] |
| `braketilt_strength`, `braketilt_lingering` | Regen braking feel | [[tuning-ride-feel|Tuning Ride Feel]], [[brake-tilt|Brake Tilt]] |
| `turntilt_strength`, `turntilt_angle_limit`, `turntilt_start_angle`, `turntilt_start_erpm`, `turntilt_speed`, `turntilt_erpm_boost`, `turntilt_erpm_boost_end`, `turntilt_yaw_aggregate` | Turn lean feel | [[tuning-ride-feel|Tuning Ride Feel]], [[turn-tilt|Turn Tilt]] |
| `booster_angle`, `booster_ramp`, `booster_current`, `brkbooster_angle`, `brkbooster_ramp`, `brkbooster_current` | High-angle current boost | [[tuning-ride-feel|Tuning Ride Feel]], [[booster|Booster]] |
| `tiltback_duty`, `tiltback_duty_angle`, `tiltback_duty_speed`, `tiltback_hv`, `tiltback_hv_angle`, `tiltback_hv_speed`, `tiltback_lv`, `tiltback_lv_angle`, `tiltback_lv_speed`, `tiltback_speed`, `tiltback_constant`, `tiltback_constant_erpm`, `tiltback_variable`, `tiltback_variable_max`, `tiltback_variable_erpm`, `tiltback_return_speed` | Speed/duty/voltage limits | [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]], [[pushback-tiltback|Pushback and Tiltback System]] |
| `noseangling_speed` | Pushback speed nose angle | [[nose-angling|Nose Angling and Pushback Speed Control]] |
| `startup_pitch_tolerance`, `startup_roll_tolerance`, `startup_speed`, `startup_click_current`, `startup_simplestart_enabled`, `startup_pushstart_enabled`, `startup_dirtylandings_enabled`, `parking_brake_mode` | Startup / engagement | [[tuning-engagement|Tuning Engagement and Startup]] |
| `fault_pitch`, `fault_roll`, `fault_adc1`, `fault_adc2`, `fault_delay_pitch`, `fault_delay_roll`, `fault_delay_switch_half`, `fault_delay_switch_full`, `fault_adc_half_erpm`, `fault_is_dual_switch`, `fault_moving_fault_disabled`, `fault_darkride_enabled`, `fault_reversestop_enabled`, `enable_quickstop`, `persistent_fatal_error` | Fault detection / safety | [[tuning-engagement|Tuning Engagement and Startup]], [[fault-detection|Fault Detection]] |
| `mc_*` (motor controller) | BLDC hardware limits | [[bldc-mc-configuration|BLDC mc_configuration Reference]] |

For exact defaults and ranges for every field above, see [[parameter-map|Parameter Map: Code ↔ VESC Tool]].

---

## Algorithm Interaction Map

Some subsystems interact — changing one affects the apparent behavior of another. Check these when a change has unexpected side effects.

- **ATR + TorqueTilt** are arbitrated in [[setpoint-composition|Setpoint Composition]]: if they push in the same direction, only the larger wins. Tuning one can mask the other.
- **PID + ATR**: A poorly tuned PID (especially low `kp2`) will oscillate when ATR adds a tilt step. Stabilize PID first.
- **BrakeTilt + ATR**: BrakeTilt is summed with ATR before the arbitration step. They reinforce each other during regen on hills.
- **Mahony filter + PID**: `mahony_kp` controls how quickly the pitch estimate tracks. Too high = noisy `balance_pitch` = oscillation even with correct PID gains.
- **TorqueTilt filter (`atr_filter`)**: This parameter is shared between ATR and TorqueTilt — it sets the Biquad cutoff on `dir_current` used by both. Changing it for ATR also changes TorqueTilt responsiveness.

See [[setpoint-composition|Setpoint Composition]] for the full arbitration logic.

---

## Telemetry Fields to Watch

When diagnosing live, these are the most useful fields to observe in VESC Tool's real-time charts:

| Field | What it tells you | Relevant tuning |
|-------|-------------------|-----------------|
| `balance_pitch` | Board's actual pitch angle estimate | [[tuning-mahony|Mahony filter]] if noisy or drifting |
| `setpoint` | Combined tilt target the PID tracks | [[setpoint-composition|Setpoint Composition]] |
| `motor_current` | Output of PID + booster | [[tuning-pid|PID]] |
| `atr.accel_diff` | ATR's terrain error signal | [[tuning-atr|ATR]] — should be ~0 on flat ground |
| `atr.setpoint` | ATR's tilt contribution | [[tuning-atr|ATR]] |
| `filt_current` | Low-pass filtered directional current | [[atr|ATR]], [[torque-tilt|TorqueTilt]] |
| `motor.acceleration` | 40-sample ERPM delta rate | [[atr|ATR]], [[traction-control|Traction Control]] |
| `duty_cycle` | Motor duty (0–1) | [[tuning-tiltbacks|Tiltbacks]] — watch near limits |
| `batt_voltage` | Battery voltage | [[tuning-tiltbacks|Tiltbacks]] — LV/HV thresholds |

---

## Key Source Files

If you need to verify behavior against code, the most relevant files are:

| File | Contains |
|------|----------|
| `refloat/src/main.c` | Main loop, IMU callback, setpoint assembly |
| `refloat/src/pid.c` | PID computation |
| `refloat/src/atr.c` | ATR algorithm, speed bands, arbitration |
| `refloat/src/motor_data.c` | Telemetry filtering (Biquad, SMA, EMA) |
| `refloat/src/conf/datatypes.h` | All `RefloatConfig` fields with types |
| `refloat/vesc_pkg_lib/vesc_c_if.h` | BLDC API surface available to Refloat |

---

## References

- [[vault-home|Vault Home]] — full note index
- [[how-to-tune|How to Tune Your Onewheel]] — human-readable tuning walkthrough
- [[parameter-map|Parameter Map: Code ↔ VESC Tool]] — every `RefloatConfig` field mapped to its VESC Tool UI label, default, and range
- [[refloat-config|RefloatConfig]] — complete parameter narrative with tuning context
- [[setpoint-composition|Setpoint Composition]] — how all tilt signals combine
- [[system-overview|System Overview]] — architecture context
