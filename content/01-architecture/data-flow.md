---
title: "Data Flow: From Sensor to PWM"
aliases:
  - "Data Flow: From Sensor to PWM"
tags:
  - architecture
  - dataflow
  - trace
  - refloat
  - bldc
date: 2026-04-16
source_files:
  - refloat/src/main.c
  - refloat/src/balance_filter.c
  - refloat/src/pid.c
  - bldc/motor/mcpwm_foc.c
---

# Data Flow: From Sensor to PWM

One complete control cycle — from the moment the gyroscope produces a reading to the moment the PWM duty cycle updates — touches both codebases, three coordinate transforms, and a PID controller. This note traces that path end to end.

---

## Complete Cycle Diagram

```
┌─────────────────────────────────────────────────────┐
│  IMU HARDWARE (~20 kHz interrupt)                   │
│                                                     │
│  Gyro: [ωx, ωy, ωz] rad/s                          │
│  Accel: [ax, ay, az] m/s²                           │
└───────────────────┬─────────────────────────────────┘
                    │ passed to bldc IMU ISR
                    ▼
┌─────────────────────────────────────────────────────┐
│  REFLOAT: imu_ref_callback()                        │
│                                                     │
│  balance_filter_update()          [balance_filter.c]│
│    Mahony: q += gyro*dt + kp*(accel×gravity)        │
│    → quaternion [q0, q1, q2, q3]                    │
│                                                     │
│  imu_update()                     [imu.c]           │
│    quaternion → Euler angles                        │
│    → balance_pitch (degrees)                        │
│    → pitch_rate   (degrees/s, from gyro Y)          │
│                                                     │
│  pid_control()                    [pid.c]           │
│    error    = setpoint - balance_pitch              │
│    P        = kp * error * scale                    │
│    I       += ki * error * dt * scale               │
│    rate_P   = kp2 * (-pitch_rate) * scale           │
│    → balance_current = P + I + rate_P               │
│                                                     │
│  booster_update()                 [booster.c]       │
│    proportional = setpoint - pitch                  │
│    → booster_current (if > booster_angle)           │
│                                                     │
│  motor_control_apply()            [motor_control.c] │
│    new_current = balance_current + booster_current  │
│    clamp(new_current, -current_min, current_max)    │
│    VESC_IF->mc_set_current(new_current)             │
└───────────────────┬─────────────────────────────────┘
                    │ VESC_IF->mc_set_current()
                    ▼
┌─────────────────────────────────────────────────────┐
│  BLDC: mc_interface_set_current()                   │
│                                                     │
│  m_iq_set = current / correction_factor             │
│  (writes into motor_all_state_t)                    │
└───────────────────┬─────────────────────────────────┘
                    │ next FOC ISR reads m_iq_set
                    ▼
┌─────────────────────────────────────────────────────┐
│  BLDC: mcpwm_foc_adc_int_handler()  [mcpwm_foc.c]  │
│                                                     │
│  ADC reads: ia, ib (phase currents)                 │
│  ADC reads: v_bus (battery voltage)                 │
│                                                     │
│  Clarke transform:                                  │
│    i_alpha = ia                                     │
│    i_beta  = (ia + 2*ib) / √3                       │
│                                                     │
│  Park transform:                                    │
│    id = cos(θ)*i_alpha + sin(θ)*i_beta              │
│    iq = cos(θ)*i_beta  - sin(θ)*i_alpha             │
│                                                     │
│  PI control:                                        │
│    vd = Kp*(id_target - id) + Ki*∫(id_err)         │
│    vq = Kp*(iq_target - iq) + Ki*∫(iq_err)         │
│    (id_target = 0; iq_target = m_iq_set from above) │
│                                                     │
│  Inverse Park:                                      │
│    v_alpha = cos(θ)*vd - sin(θ)*vq                  │
│    v_beta  = sin(θ)*vd + cos(θ)*vq                  │
│                                                     │
│  Space Vector Modulation:                           │
│    (v_alpha, v_beta) → (duty_A, duty_B, duty_C)     │
│                                                     │
│  PWM timer update:                                  │
│    TIM1->CCR1/2/3 = duty_A/B/C                      │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
         Motor phases energized
         Rotor torque applied
         Board tilts / resists tilting
```

---

## Meanwhile: The Main Thread (1 kHz)

In parallel, at 1/20th the rate, the main thread is computing the **setpoint** that the IMU callback consumes:

```
Main thread (refloat_thd):

  motor_data_update()        → ERPM, current, accel, duty, voltage, temps
  footpad_sensor_update()    → FS_NONE / LEFT / RIGHT / BOTH
  
  calculate_setpoint_target() → base setpoint (tiltbacks, SAT state)
  apply_noseangling()         → speed-dependent nose offset
  torque_tilt_update()        → current-proportional tilt
  atr_update()                → terrain adaptation tilt
  brake_tilt_update()         → braking nose lift
  turn_tilt_update()          → yaw-based corner tilt
  
  → data.setpoint = base + noseangling + turntilt
                  + arbitrate(atr+braketilt, torquetilt)

  check_faults()              → may transition RUNNING → READY
```

The `data.setpoint` written here is read by the IMU callback's `pid_control()` call. The main thread writes it; the IMU callback reads it.

---

## Key Variables at Each Stage

| Variable | Type | Updated By | Consumed By |
|----------|------|-----------|-------------|
| `imu.balance_pitch` | float (°) | IMU callback (Mahony) | PID `error` |
| `imu.pitch_rate` | float (°/s) | IMU callback (gyro Y) | PID `rate_P` |
| `data.setpoint` | float (°) | Main thread | PID `error` |
| `motor_control.requested_current` | float (A) | IMU callback (PID+booster) | `motor_control_apply()` |
| `motor.erpm` | float | Main thread | ATR, TorqueTilt, TurnTilt |
| `motor.filt_current` | float (A) | Main thread (Biquad) | ATR, TorqueTilt |
| `motor.acceleration` | float | Main thread (SMA-40) | ATR |
| `m_iq_set` | float | bldc mc_interface | FOC PI loop |

---

## Latency Budget

| Stage | Latency |
|-------|---------|
| IMU hardware → callback | ~0 µs (direct ISR call) |
| Mahony filter update | ~5–10 µs |
| PID computation | ~2–5 µs |
| `mc_set_current` write | ~1 µs |
| FOC ISR execution | ~30–50 µs (at 20 kHz) |
| PWM timer update | ~1 µs |
| **Total: sensor to PWM** | **~50–70 µs** |

Setpoint latency (main thread → IMU callback consumption): up to 1 ms, but setpoints are rate-limited so this is not a stability concern.

---

## References

- [[mahony-ahrs-filter|Mahony AHRS Filter]] — Quaternion filter running inside `imu_ref_callback`
- [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] — Euler angle extraction from quaternion
- [[pid-controller|PID Controller]] — `pid_control()` in `pid.c:51–89`
- [[setpoint-composition|Setpoint Composition]] — how the main thread builds `data.setpoint`
- [[refloat-bldc-interface|Refloat–BLDC Interface]] — `VESC_IF->mc_set_current()` call path
- [[foc-overview|FOC Overview]] — Clarke/Park/PI/SVM chain in bldc
- [[clarke-park-transforms|Clarke and Park Transforms]] — coordinate transform mathematics
