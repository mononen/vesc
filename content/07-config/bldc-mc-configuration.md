---
title: "BLDC mc_configuration Reference"
aliases:
  - "BLDC mc_configuration Reference"
  - "BLDC mc_configuration"
  - "mc_configuration"
tags:
  - config
  - reference
  - bldc
  - foc
date: 2026-04-16
source_files:
  - bldc/datatypes.h
  - bldc/motor/mcconf_default.h
---

# BLDC mc_configuration Reference

`mc_configuration` is the motor controller configuration struct in the VESC firmware, defined in `bldc/datatypes.h:389–588`. It contains 200+ fields covering motor parameters, current limits, temperature protection, and FOC control gains.

For a onewheel, the subset below is most directly relevant to ride behavior. Refloat reads several of these values via `VESC_IF` to enforce its own safety logic.

---

## Current Limits

The most safety-critical parameters. These hard-limit motor current regardless of what Refloat commands.

| Parameter | Description |
|-----------|-------------|
| `l_current_max` | Maximum motor current (A, positive = forward torque) |
| `l_current_min` | Maximum braking/regen current (A, negative value) |
| `l_in_current_max` | Maximum battery draw current (A) |
| `l_in_current_min` | Maximum regen battery charge current (A) |
| `l_abs_current_max` | Absolute fault threshold — triggers immediate stop if exceeded |

**For onewheel use:** Set `l_current_max` to the motor's rated peak current. Too high and the motor overheats; too low and the board doesn't have enough torque to balance on steep hills or for heavy riders. Refloat reads `l_current_max` and clamps PID output accordingly.

`l_abs_current_max` should be set ~20% above `l_current_max` — it's the fault threshold, not the operating limit.

---

## FOC Core Parameters

Motor electrical parameters — typically set via VESC Tool's motor detection procedure, not manually.

| Parameter | Description |
|-----------|-------------|
| `foc_motor_l` | Stator inductance (H) — determines current loop `kp` |
| `foc_motor_ld_lq_diff` | Difference between d/q inductance (salient motors only) |
| `foc_motor_r` | Stator resistance (Ω) — determines current loop `ki` |
| `foc_motor_flux_linkage` | Permanent magnet flux linkage (Wb) — relates Iq to torque and back-EMF |
| `foc_current_kp` | Current PI proportional gain (auto-calculated from motor L) |
| `foc_current_ki` | Current PI integral gain (auto-calculated from R/L) |
| `foc_f_zv` | PWM switching frequency (Hz) — typically 20,000–30,000 |

**Do not change these manually** unless you've measured the motor parameters with an LCR meter and understand the consequences. Incorrect values cause oscillation or thermal runaway.

---

## Sensor Mode and Sensorless Parameters

| Parameter | Description |
|-----------|-------------|
| `foc_sensor_mode` | SENSORLESS, ENCODER, HALL, HFI_* variants |
| `foc_sl_erpm` | ERPM threshold above which sensorless observer is fully trusted |
| `foc_sl_erpm_start` | ERPM at which observer begins blending in |
| `foc_observer_gain` | Observer pole placement — higher = faster, potentially noisier |
| `foc_pll_kp`, `foc_pll_ki` | PLL gains for phase tracking |
| `foc_openloop_rpm` | Open-loop startup speed (ERPM) for sensorless |
| `foc_hfi_voltage_start`, `_run` | HFI (High Frequency Injection) voltages for standstill sensing |

For a hub motor with Hall sensors: set `foc_sensor_mode = FOC_SENSOR_MODE_HALL`. The sensorless parameters still matter above the Hall sensor's resolution at high speed.

---

## Duty Cycle and ERPM Limits

| Parameter | Description |
|-----------|-------------|
| `l_max_duty` | Maximum PWM duty cycle (0.95 typical) |
| `l_min_duty` | Minimum non-zero duty (0.005 typical) |
| `l_max_erpm` | Maximum electrical RPM (positive direction) |
| `l_min_erpm` | Maximum electrical RPM (negative direction) |

`l_max_erpm` limits top speed. For a onewheel, this is usually set well above the practical speed limit — the Refloat tiltbacks are the soft limit; `l_max_erpm` is the hard firmware limit.

---

## Temperature Limits

The BLDC layer handles thermal derating. As temperature rises above `_start`, current is linearly derated. At `_end`, current drops to zero.

| Parameter | Description |
|-----------|-------------|
| `l_temp_fet_start` | MOSFET temp where derating begins (°C) |
| `l_temp_fet_end` | MOSFET temp at full current cutoff (°C) |
| `l_temp_motor_start` | Motor temp where derating begins (°C) |
| `l_temp_motor_end` | Motor temp at full current cutoff (°C) |

Refloat detects when derating is active (via current limit changes) and adds a tiltback (`SAT_PB_TEMPERATURE`). See [[pushback-tiltback|Pushback and Tiltback System]].

Typical values:
- FET: start=70°C, end=95°C
- Motor: start=80°C, end=110°C (varies by winding material)

---

## Battery Voltage Limits

| Parameter | Description |
|-----------|-------------|
| `l_battery_cut_start` | Voltage where power begins reducing |
| `l_battery_cut_end` | Voltage at full power cutoff (BMS-level protection) |
| `l_min_vin` | Minimum input voltage for operation |
| `l_max_vin` | Maximum input voltage fault threshold |

Refloat's `tiltback_hv` and `tiltback_lv` should be set within the safe operating range defined by these parameters.

---

## Field Weakening

| Parameter | Description |
|-----------|-------------|
| `foc_fw_current_max` | Maximum field-weakening current (A, negative = weakening) |
| `foc_fw_duty_start` | Duty cycle threshold to begin field weakening |
| `foc_fw_ramp_time` | Ramp time for field weakening current |
| `foc_fw_q_current_factor` | Factor for q-axis current adjustment during FW |

Field weakening extends the motor's top speed beyond the back-EMF-limited maximum by injecting negative d-axis current. For a onewheel, this allows higher speeds on flat ground at the cost of reduced torque headroom. Most stock onewheel configurations don't require field weakening.

---

## Speed PID (Not Used by Refloat)

| Parameter | Description |
|-----------|-------------|
| `s_pid_kp`, `s_pid_ki`, `s_pid_kd` | Speed PID gains |
| `s_pid_loop_rate` | Speed loop rate (Hz) |

Refloat commands current directly, not speed. The speed PID loop in bldc is bypassed. These parameters are irrelevant for balance control.

---

## References

- [[bldc/datatypes.h]] — `mc_configuration` struct lines 389–588
- [[bldc/motor/mcconf_default.h]] — default values for all parameters
- [[foc-overview|FOC Overview]] — how these parameters affect the FOC inner loop
- [[current-pi-loop|Current PI Loop]] — `foc_current_kp/ki`, `foc_motor_l/r` used for gain calculation
- [[space-vector-modulation|Space Vector Modulation]] — `l_max_duty` limit applied before SVM output
- [[pushback-tiltback|Pushback and Tiltback System]] — Refloat reads temp/voltage limits for SAT triggering
- [[refloat-bldc-interface|Refloat–BLDC Interface]] — how Refloat accesses `mc_configuration` values
