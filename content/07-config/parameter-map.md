---
title: "Parameter Map: Code ↔ VESC Tool"
aliases:
  - "Parameter Map"
  - "parameter-map"
tags:
  - config
  - reference
  - parameters
  - vesc-tool
date: 2026-04-16
source_files:
  - refloat/src/conf/datatypes.h
  - refloat/src/conf/settings.xml
---

# Parameter Map: Code ↔ VESC Tool

Maps every `RefloatConfig` C struct field to its VESC Tool UI label, with default value and valid range. Use this when a user mentions a UI label and you need to find the code variable (or vice versa).

Source of truth: `refloat/src/conf/settings.xml` (labels, defaults, ranges) and `refloat/src/conf/datatypes.h` (types).

---

## Balance — PID

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `kp` | Angle P | 20 | 0–40 | — |
| `kp2` | Rate P | 0.6 | 0–3 | — |
| `ki` | Angle I | 0.005 | 0–0.5 | — |
| `kp_brake` | Angle P (Braking) | 1.0× | 0.2–3 | multiplier of kp |
| `kp2_brake` | Rate P (Braking) | 1.0× | 0–3 | multiplier of kp2 |
| `ki_limit` | I Term Limit | 30 | 0–500 | A |
| `brake_current` | Brake Current | 6 | 0–100 | A |

**Notes:**
- `kp_brake` and `kp2_brake` are *multipliers* of `kp`/`kp2`, not absolute values (suffix `x` in UI)
- `ki_limit` caps the integrator — prevents windup; rarely needs changing

---

## IMU / Mahony Filter

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `mahony_kp` | Pitch KP | 2.0 | 0.2–3 | — |
| `mahony_kp_roll` | Roll KP | 1.4 | 0–3 | — |
| `hertz` | Loop Hertz | 832 | 50–4000 | Hz |

**Notes:**
- `hertz` should match or be a multiple of the IMU hardware sample rate (832 Hz for LSM6DS3, 800 Hz for BMI160)
- `mahony_kp_roll` < `mahony_kp` is recommended to prevent pitch bleed-in during turns

---

## ATR — Adaptive Terrain Response

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `atr_strength_up` | ATR Uphill Strength | 1.0 | 0–3.5 | — |
| `atr_strength_down` | ATR Downhill Strength | 0.5 | 0–3.5 | — |
| `atr_threshold_up` | Threshold Angle Up | 1.5 | 0–5 | ° |
| `atr_threshold_down` | Threshold Angle Down | 1.5 | 0–5 | ° |
| `atr_speed_boost` | Speed Boost | 0.3 | −1–1 | fraction |
| `atr_angle_limit` | Tiltback Angle Limit | 8 | 0–30 | ° |
| `atr_on_speed` | Max Tiltback Speed | 10 | 0–100 | °/s |
| `atr_off_speed` | Max Tiltback Release Speed | 8 | 0–100 | °/s |
| `atr_response_boost` | Tiltback Response Boost | 1.5 | 1–2 | × |
| `atr_transition_boost` | Tiltback Transition Boost | 3 | 1–10 | × |
| `atr_filter` | Current Filter | 5 | 0–20 | Hz |
| `atr_amps_accel_ratio` | Amps to Acceleration Ratio | 9 | 5–30 | — |
| `atr_amps_decel_ratio` | Amps to Deceleration Ratio | 8 | 4–30 | — |

**Notes:**
- `atr_filter` is a Biquad low-pass cutoff on `dir_current` — shared with TorqueTilt
- `atr_speed_boost` applies a fractional boost at high ERPM; negative value inverts effect
- `atr_amps_accel_ratio` calibrates the physics model; tune until `accel_diff ≈ 0` on flat ground

---

## Torque Tilt

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `torquetilt_start_current` | Start Current Threshold | 15 | 0–100 | A |
| `torquetilt_angle_limit` | Tiltback Angle Limit | 8 | 0–30 | ° |
| `torquetilt_on_speed` | Max Tiltback Speed | 10 | 0–100 | °/s |
| `torquetilt_off_speed` | Max Tiltback Release Speed | 8 | 0–100 | °/s |
| `torquetilt_strength` | Strength | 0.1 | 0–1 | °/A |
| `torquetilt_strength_regen` | Strength (Regen) | 0.1 | 0–1 | °/A |

**Notes:**
- Activates when `|filt_current| > torquetilt_start_current`
- `torquetilt_strength_regen` applies during braking/regen; can be set lower than accel strength

---

## Brake Tilt

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `braketilt_strength` | Brake Tilt Strength | 0 | 0–20 | — |
| `braketilt_lingering` | Brake Tilt Lingering | 2 | 1–5 | — |

**Notes:**
- Default strength is 0 (disabled). Increase to add nose-lift feel when braking
- `braketilt_lingering` controls how long the tilt persists after braking ends

---

## Turn Tilt

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `turntilt_strength` | Strength | 0 | −30–30 | — |
| `turntilt_angle_limit` | Tiltback Angle Limit | 3 | 0–30 | ° |
| `turntilt_start_angle` | Turn Aggregate Threshold | 5 | 0–45 | ° |
| `turntilt_start_erpm` | ERPM Threshold | 2000 | 100–100000 | ERPM |
| `turntilt_speed` | Max Tiltback Speed | 5 | 0–100 | °/s |
| `turntilt_erpm_boost` | Speed Boost % | 200 | 0–10000 | % |
| `turntilt_erpm_boost_end` | Speed Boost Max ERPM | 5000 | 100–100000 | ERPM |
| `turntilt_yaw_aggregate` | Turn Aggregate Target | 90 | 50–360 | ° |

**Notes:**
- Default strength is 0 (disabled). Negative values tilt the board outward in turns
- `turntilt_yaw_aggregate` is the total yaw rotation needed to reach full tilt strength
- `turntilt_erpm_boost` adds extra tilt effect at speed (% boost at `turntilt_erpm_boost_end`)

---

## Booster

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `booster_angle` | Start Angle (Accel) | 8 | 0–15 | ° |
| `booster_ramp` | Ramp Up (Accel) | 4 | 1–10 | ° |
| `booster_current` | Current Boost (Accel) | 0 | 0–100 | A |
| `brkbooster_angle` | Start Angle (Brake) | 8 | 0–15 | ° |
| `brkbooster_ramp` | Ramp Up (Brake) | 4 | 1–10 | ° |
| `brkbooster_current` | Current Boost (Brake) | 0 | 0–100 | A |

**Notes:**
- Default current is 0 (disabled) for both accel and brake boosters
- Booster adds current when `|pitch - setpoint| > booster_angle`, ramping over `booster_ramp` degrees

---

## Nose Angling

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `noseangling_speed` | Nose Angling Speed | 5 | 0–100 | °/s |

**Notes:**
- Controls the rate at which constant/variable tiltbacks and pushback ramp in
- Also governs how quickly nose angle adjusts during speed-based pushback transitions

---

## Pushback / Tiltback

### Duty Cycle Pushback
| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `tiltback_duty` | Duty Cycle Threshold | 80% | 0–100% | % |
| `tiltback_duty_angle` | Pushback Angle | 5 | 0–30 | ° |
| `tiltback_duty_speed` | Pushback Speed | 3 | 0–30 | °/s |

### High Voltage Pushback
| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `tiltback_hv` | High Voltage Threshold | 4.3 | 0–150 | V (per-cell on fw 6.05+) |
| `tiltback_hv_angle` | Pushback Angle | 8 | 0–30 | ° |
| `tiltback_hv_speed` | Speed | 1 | 0–30 | °/s |

### Low Voltage Pushback
| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `tiltback_lv` | Low Voltage Threshold | 3.0 | 0–150 | V (per-cell on fw 6.05+) |
| `tiltback_lv_angle` | Pushback Angle | 10 | 0–30 | ° |
| `tiltback_lv_speed` | Speed | 1 | 0–30 | °/s |

### Speed Pushback
| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `tiltback_speed` | Speed Threshold | 0 | 0–100 | km/h |

### Constant / Variable Tiltback (Ride Angle)
| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `tiltback_constant` | Constant Tiltback | 0 | −10–10 | ° |
| `tiltback_constant_erpm` | Constant Tiltback ERPM | 500 | 200–100000 | ERPM |
| `tiltback_variable` | Variable Tiltback Rate | 0.3 | 0–5 | °/1000 ERPM |
| `tiltback_variable_max` | Variable Tiltback Target | 0 | −10–10 | ° |
| `tiltback_variable_erpm` | Variable Tiltback Start ERPM | 0 | 0–100000 | ERPM |
| `tiltback_return_speed` | Return To Level Speed | 1 | 0–10 | °/s |

**Notes:**
- `tiltback_duty` default is 80% — VESC hard limit is 95%; reaching it causes nosedive
- Constant Tiltback should not substitute for IMU calibration (riding backward gives opposite effect)
- HV/LV thresholds are per-cell on fw 6.05+; multiply by cell count on older firmware

---

## Fault Detection

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `fault_pitch` | Pitch Axis Fault Cutoff | 60 | 45–90 | ° |
| `fault_roll` | Roll Axis Fault Cutoff | 60 | 45–90 | ° |
| `fault_adc1` | ADC1 Switch Voltage | 2.0 | 0–3.3 | V |
| `fault_adc2` | ADC2 Switch Voltage | 2.0 | 0–3.3 | V |
| `fault_delay_pitch` | Pitch Fault Delay | 250 | 0–10000 | ms |
| `fault_delay_roll` | Roll Fault Delay | 250 | 0–10000 | ms |
| `fault_delay_switch_half` | Half Switch Fault Delay | 250 | 0–10000 | ms |
| `fault_delay_switch_full` | Full Switch Fault Delay | 250 | 0–10000 | ms |
| `fault_adc_half_erpm` | ADC Half State Fault ERPM | 200 | 0–100000 | ERPM |
| `fault_is_dual_switch` | Treat Both Sensors as One (Posi) | false | bool | — |
| `fault_moving_fault_disabled` | Disable Moving Faults | false | bool | — |
| `fault_darkride_enabled` | Enable Darkride | false | bool | — |
| `fault_reversestop_enabled` | Enable Reverse Stop | false | bool | — |
| `enable_quickstop` | Enable Quickstop | true | bool | — |
| `persistent_fatal_error` | Persistent Fatal Error | true | bool | — |

**Notes:**
- `fault_adc1/2` = footpad voltage threshold; set to 0 to disable that sensor zone
- `fault_adc_half_erpm` = speed below which one-zone contact triggers fault
- `fault_is_dual_switch` (Posi mode) treats both sensors as one zone — disables heel-lift dismount

---

## Startup

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `startup_pitch_tolerance` | Startup Pitch Axis Angle Tolerance | 4 | 0–80 | ° |
| `startup_roll_tolerance` | Startup Roll Axis Angle Tolerance | 45 | 0–80 | ° |
| `startup_speed` | Startup Centering Speed | 30 | 0–100 | °/s |
| `startup_click_current` | Start/Stop Click Current | 0 | 0–20 | A |
| `startup_simplestart_enabled` | Enable Simple Start | false | bool | — |
| `startup_pushstart_enabled` | Enable Push Start | false | bool | — |
| `startup_dirtylandings_enabled` | Enable Dirty Landings | false | bool | — |
| `parking_brake_mode` | Parking Brake | IDLE | enum | — |

---

## Remote / Input Tilt

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `inputtilt_remote_type` | Remote Type | NONE | enum | NONE/UART/PPM |
| `inputtilt_angle_limit` | Tiltback Angle Limit | 10 | 0–90 | ° |
| `inputtilt_speed` | Tiltback Speed | 25 | 0–150 | °/s |
| `inputtilt_invert_throttle` | Invert Throttle | true | bool | — |
| `inputtilt_deadband` | Input Deadband | 10% | 0–50% | % |
| `remote_throttle_current_max` | Throttle Current Maximum | 0 | 0–50 | A |
| `remote_throttle_grace_period` | Grace Period | 10 | 0–60 | s |

---

## Haptic Feedback

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `haptic.duty.frequency` | Warning Audible Frequency | 495 | 300–1000 | Hz |
| `haptic.duty.strength` | Warning Audible Strength | 3 | 0–12 | V |
| `haptic.error.frequency` | Error Audible Frequency | 550 | 300–1000 | Hz |
| `haptic.error.strength` | Error Audible Strength | 3 | 0–12 | V |
| `haptic.vibrate.frequency` | Vibrate Frequency | 70 | 10–200 | Hz |
| `haptic.vibrate.strength` | Vibrate Strength | 0 | 0–25 | A |
| `haptic.duty_solid_offset` | Duty Cycle Solid Offset | 5% | 0–100% | % |
| `haptic.current_threshold` | Current Threshold | 0% | 0–100% | % |
| `haptic.min_strength` | Minimum Strength | 20% | 0–100% | % |
| `haptic.max_strength_speed` | Maximum Strength Speed | 30 | 10–100 | km/h |
| `haptic.strength_curvature` | Strength Curvature | 0.6 | 0–1 | — |
| `is_beeper_enabled` | Enable Beeper on Servo/PPM | false | bool | — |
| `is_dutybeep_enabled` | Beep on Duty Pushback | false | bool | — |
| `is_footbeep_enabled` | Beep on Sensor Fault | true | bool | — |

---

## BMS Integration

| C Field | VESC Tool Label | Default | Range | Unit |
|---------|----------------|---------|-------|------|
| `bms.enabled` | Enable BMS Integration | false | bool | — |
| `bms.cell_lv_threshold` | Cell Low Voltage Threshold | 2.7 | 2.5–4.5 | V |
| `bms.cell_hv_threshold` | Cell High Voltage Threshold | 4.3 | 2.5–4.5 | V |
| `bms.cell_balance_threshold` | Cell Balance Threshold | 0.2 | 0.01–1 | V |
| `bms.cell_ht_threshold` | Cell High Temp Threshold | 45 | 0–60 | °C |
| `bms.cell_lt_threshold` | Cell Low Temp Threshold | 0 | −20–20 | °C |
| `bms.bms_ht_threshold` | BMS High Temp Threshold | 60 | 0–80 | °C |

---

## General

| C Field | VESC Tool Label | Default | Unit |
|---------|----------------|---------|------|
| `disabled` | Disable Package | false | bool |
| `persistent_fatal_error` | Persistent Fatal Error | true | bool |

---

## References

- [[refloat-config|RefloatConfig]] — full parameter narrative with tuning context
- [[tuning-agent-index|Tuning Agent Index]] — symptom-to-parameter navigation
- `refloat/src/conf/datatypes.h` — C struct definition
- `refloat/src/conf/settings.xml` — UI labels, defaults, ranges (source of this table)
