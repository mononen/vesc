---
title: "RefloatConfig"
aliases:
  - "RefloatConfig"
  - "RefloatConfig Reference"
tags:
  - config
  - reference
  - refloat
  - tuning
date: 2026-04-16
source_files:
  - refloat/src/conf/datatypes.h
---

# RefloatConfig Reference

`RefloatConfig` is the main configuration struct for the Refloat package, defined in `src/conf/datatypes.h:208–312`. All user-tunable parameters live here. They are serialized to VESC EEPROM and persist across power cycles.

This note is a parameter reference. For tuning guidance, see the linked tuning notes.

---

## PID Control

| Parameter | Type | Description |
|-----------|------|-------------|
| `kp` | float | Proportional gain on pitch error |
| `ki` | float | Integral gain on pitch error |
| `kp2` | float | Pitch-rate (derivative) gain |
| `ki_limit` | float | Max integral accumulation (0 = unlimited) |
| `kp_brake` | float | Multiplier on `kp` during deceleration (0–1) |
| `kp2_brake` | float | Multiplier on `kp2` during deceleration (0–1) |

→ [[tuning-pid|Tuning the PID Controller]] · [[pid-controller|PID Controller]]

---

## IMU / Filter

| Parameter | Type | Description |
|-----------|------|-------------|
| `mahony_kp` | float | Mahony filter gain for pitch axis |
| `mahony_kp_roll` | float | Mahony filter gain for roll axis |
| `hertz` | uint16_t | Target main loop frequency (Hz) |

→ [[tuning-mahony|Tuning the Mahony Filter]] · [[mahony-ahrs-filter|Mahony AHRS Filter]]

---

## Booster

| Parameter | Type | Description |
|-----------|------|-------------|
| `booster_angle` | float | Pitch error threshold for boost activation (°) |
| `booster_ramp` | float | Current ramp rate (A per ° beyond threshold) |
| `booster_current` | float | Maximum boost current (A) |
| `brkbooster_angle` | float | Same as booster_angle but for braking direction |
| `brkbooster_ramp` | float | Braking boost ramp rate |
| `brkbooster_current` | float | Max braking boost current (A) |

→ [[Booster]] · [[tuning-ride-feel|Tuning Ride Feel]]

---

## ATR — Adaptive Terrain Response

| Parameter | Type | Description |
|-----------|------|-------------|
| `atr_strength_up` | float | Tilt strength when terrain resists (uphill/headwind) |
| `atr_strength_down` | float | Tilt strength when terrain assists (downhill) |
| `atr_threshold_up` | float | Min accel_diff to activate upward ATR |
| `atr_threshold_down` | float | Min accel_diff to activate downward ATR |
| `atr_on_speed` | float | Ramp speed engaging ATR tilt (°/s) |
| `atr_off_speed` | float | Ramp speed disengaging ATR tilt (°/s) |
| `atr_angle_limit` | float | Max ATR setpoint angle (°) |
| `atr_speed_boost` | float | Extra ATR multiplier above 3000 ERPM |
| `atr_response_boost` | float | Boost during rapid target direction change |
| `atr_transition_boost` | float | Extra ramp speed on direction reversal |
| `atr_filter` | float | Biquad cutoff Hz for current signal (shared with TorqueTilt) |
| `atr_amps_accel_ratio` | float | Expected accel per amp (forward) |
| `atr_amps_decel_ratio` | float | Expected accel per amp (braking) |

→ [[atr|ATR — Adaptive Terrain Response]] · [[tuning-atr|Tuning ATR]]

---

## TorqueTilt

| Parameter | Type | Description |
|-----------|------|-------------|
| `torquetilt_start_current` | float | Current threshold to begin tilt (A) |
| `torquetilt_strength` | float | °/A above threshold (acceleration) |
| `torquetilt_strength_regen` | float | °/A above threshold (braking/regen) |
| `torquetilt_on_speed` | float | Ramp-up speed (°/s) |
| `torquetilt_off_speed` | float | Ramp-down speed (°/s) |
| `torquetilt_angle_limit` | float | Max TorqueTilt setpoint (°) |

→ [[torque-tilt|Torque Tilt]] · [[tuning-ride-feel|Tuning Ride Feel]]

---

## BrakeTilt

| Parameter | Type | Description |
|-----------|------|-------------|
| `braketilt_strength` | float | Strength of nose lift during braking (5–25) |
| `braketilt_lingering` | float | How long effect persists after braking ends |

→ [[brake-tilt|Brake Tilt]] · [[tuning-ride-feel|Tuning Ride Feel]]

---

## TurnTilt

| Parameter | Type | Description |
|-----------|------|-------------|
| `turntilt_strength` | float | °/° of aggregate yaw |
| `turntilt_angle_limit` | float | Max TurnTilt setpoint (°) |
| `turntilt_start_angle` | float | Min aggregate yaw to activate (°) |
| `turntilt_start_erpm` | float | Min speed to activate (ERPM) |
| `turntilt_speed` | float | Ramp speed (°/s) |
| `turntilt_erpm_boost` | float | ERPM where speed boost begins |
| `turntilt_erpm_boost_end` | float | ERPM where speed boost reaches max |
| `turntilt_yaw_aggregate` | float | Yaw accumulation window (ms) |

→ [[turn-tilt|Turn Tilt]] · [[tuning-ride-feel|Tuning Ride Feel]]

---

## Tiltbacks / Pushback

| Parameter | Type | Description |
|-----------|------|-------------|
| `tiltback_duty` | float | Duty cycle trigger (0–1) |
| `tiltback_duty_angle` | float | Nose angle at duty/speed tiltback (°) |
| `tiltback_duty_speed` | float | Ramp speed for duty/speed tiltback (°/s) |
| `tiltback_speed` | float | Speed trigger (km/h) |
| `tiltback_variable` | float | Nose angle per ERPM above threshold |
| `tiltback_variable_erpm` | float | ERPM where variable tiltback starts |
| `tiltback_variable_max` | float | Max angle from variable tiltback (°) |
| `tiltback_constant` | float | Fixed nose angle above constant_erpm (°) |
| `tiltback_constant_erpm` | float | ERPM threshold for constant tiltback |
| `noseangling_speed` | float | Rate of noseangling change (°/s) |
| `tiltback_hv` | float | High voltage trigger (V) |
| `tiltback_hv_angle` | float | Nose angle at HV tiltback (°) |
| `tiltback_hv_speed` | float | Ramp speed for HV tiltback (°/s) |
| `tiltback_lv` | float | Low voltage trigger (V) |
| `tiltback_lv_angle` | float | Nose angle at LV tiltback (°) |
| `tiltback_lv_speed` | float | Ramp speed for LV tiltback (°/s) |
| `tiltback_return_speed` | float | Speed to return nose to level (°/s) |

→ [[pushback-tiltback|Pushback and Tiltback System]] · [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] · [[nose-angling|Nose Angling and Pushback Speed Control]]

---

## Fault Detection

| Parameter | Type | Description |
|-----------|------|-------------|
| `fault_pitch` | float | Max pitch angle before stop (°) |
| `fault_roll` | float | Max roll angle before stop (°) |
| `fault_adc1` | float | Front footpad activation threshold (V) |
| `fault_adc2` | float | Rear footpad activation threshold (V) |
| `fault_delay_pitch` | uint16_t | Pitch fault delay (ms) |
| `fault_delay_roll` | uint16_t | Roll fault delay (ms) |
| `fault_delay_switch_half` | uint16_t | Single-pad fault delay at low speed (ms) |
| `fault_delay_switch_full` | uint16_t | No-pad fault delay (ms) |
| `fault_adc_half_erpm` | float | Max ERPM for half-switch fault (ERPM) |
| `fault_is_dual_switch` | bool | Require both pads for engagement |
| `fault_moving_fault_disabled` | bool | Suppress switch faults while moving |
| `fault_darkride_enabled` | bool | Allow upside-down riding |
| `fault_reversestop_enabled` | bool | Enable reverse stop protection |
| `enable_quickstop` | bool | Enable low-speed quickstop |

→ [[fault-detection|Fault Detection]] · [[tuning-engagement|Tuning Engagement and Startup]]

---

## Startup

| Parameter | Type | Description |
|-----------|------|-------------|
| `startup_pitch_tolerance` | float | Max pitch for valid startup (°) |
| `startup_roll_tolerance` | float | Max roll for valid startup (°) |
| `startup_speed` | float | Setpoint centering speed on engage (°/s) |
| `startup_click_current` | float | Haptic click current on engagement (A) |
| `startup_simplestart_enabled` | bool | Allow single-pad start after 2s |
| `startup_pushstart_enabled` | bool | Allow push-start while rolling |
| `startup_dirtylandings_enabled` | bool | Expanded pitch tolerance for dirty landings |

→ [[tuning-engagement|Tuning Engagement and Startup]] · [[state-machine|State Machine]]

---

## Motor Control

| Parameter | Type | Description |
|-----------|------|-------------|
| `parking_brake_mode` | enum | ALWAYS / IDLE / NEVER |
| `brake_current` | float | Parking brake current (A) |

---

## Audio / Haptic

| Parameter | Type | Description |
|-----------|------|-------------|
| `is_beeper_enabled` | bool | Enable audible beeper |
| `is_dutybeep_enabled` | bool | Continuous beep during duty tiltback |
| `is_footbeep_enabled` | bool | Beep when footpad released at speed |
| `haptic` | CfgHapticFeedback | Haptic feedback configuration |

---

## References

- [[refloat/src/conf/datatypes.h]] — `RefloatConfig` struct definition lines 208–312
- [[pid-controller|PID Controller]], [[mahony-ahrs-filter|Mahony AHRS Filter]], [[Booster]] — use PID/IMU parameters
- [[atr|ATR — Adaptive Terrain Response]], [[torque-tilt|Torque Tilt]], [[brake-tilt|Brake Tilt]], [[turn-tilt|Turn Tilt]] — ride-feel parameters
- [[pushback-tiltback|Pushback and Tiltback System]], [[fault-detection|Fault Detection]], [[state-machine|State Machine]] — safety parameters
