---
title: "ATR — Adaptive Terrain Response"
aliases:
  - "ATR — Adaptive Terrain Response"
  - "ATR"
tags:
  - ride-feel
  - atr
  - terrain
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/atr.c
  - refloat/src/atr.h
  - refloat/src/motor_data.c
---

# ATR — Adaptive Terrain Response

ATR computes a setpoint offset that tilts the board's nose based on the difference between how much the motor *should* be accelerating the board (based on current) and how much it *actually* is (based on measured acceleration). This difference reveals terrain conditions: uphill, downhill, headwind, rough surface.

ATR is one of the two algorithms that feeds the terrain-vs-current arbitration in [[setpoint-composition|Setpoint Composition]].

---

## The Core Insight

On flat ground at constant speed, motor current directly predicts acceleration. If you know the motor current and the motor's characteristics, you can predict how fast the board should be speeding up or slowing down.

On a hill, the terrain adds or removes force from the system:
- **Uphill:** Motor draws more current than a flat surface would require → less acceleration than the current predicts → positive `accel_diff`
- **Downhill:** Gravity assists → more acceleration than current predicts → negative `accel_diff`

ATR uses this signal to proactively tilt the board, rather than waiting for the PID to react.

---

## Computing `accel_diff`

```c
// atr.c
measured_accel = motor.acceleration.sma / loop_hz   // ERPM/s → normalized
expected_accel = (motor.filt_current - offset) / accel_ratio

accel_diff = expected_accel - measured_accel
```

`motor.filt_current` is the motor current filtered through a Biquad low-pass (`atr_filter` Hz cutoff) to remove high-frequency noise.

`atr_amps_accel_ratio` calibrates the linear model — it says "each amp of current should produce this many units of acceleration." If terrain is neutral, the ratio holds. Deviation from the model = terrain effect.

---

## Speed-Dependent Filter Bands

`accel_diff` is not used raw — it's smoothed through one of three EMA filters based on ERPM:

| ERPM Range | Filter Speed | Reason |
|------------|-------------|--------|
| < 1000 ERPM | Slow (high alpha) | At low speed, stop-start motion creates noisy accel readings |
| 1000–2000 ERPM | Medium | Transition zone |
| > 2000 ERPM | Fast (low alpha) | At speed, fast terrain response is needed and signal is cleaner |

This adaptive filtering means ATR is conservative at low speed (where false triggers are most likely) and responsive at speed (where terrain changes matter most).

---

## Setpoint Contribution

```c
// atr.c
if (forward && accel_diff > threshold_up):
    strength = atr_strength_up
elif (forward && accel_diff < -threshold_down):
    strength = atr_strength_down
// (reversed for backward travel)

atr_target = strength * accel_diff

// Speed boost above 3000 ERPM
speed_boost = (abs_erpm - 3000) * some_function_of_response_boost
atr_target *= (1.0 + speed_boost * atr_speed_boost)

// Rate-limit toward target
atr.setpoint → ramp toward atr_target at atr_on_speed or atr_off_speed
```

The on/off speeds are asymmetric by design: `atr_on_speed` governs how fast the tilt engages, `atr_off_speed` governs how fast it returns. Typically on > off for quick engagement, slow recovery.

When `atr_target` reverses direction (e.g., going from uphill to downhill), the `atr_response_boost` and `atr_transition_boost` parameters provide extra ramp speed to prevent lag during direction transitions.

---

## `ATR` Struct

```c
// atr.h:24–39
ATR {
    float on_speed, off_speed;         // Ramp speed parameters (from config)
    float speed_boost_mult;            // Computed speed boost multiplier
    float accel_diff;                  // Expected - measured acceleration
    float speed_boost;                 // Current speed boost value
    float ad_alpha1, ad_alpha2, ad_alpha3; // EMA coefficients for 3 speed bands
    float target;                      // Computed target tilt
    float ramped_step_size;            // Internal ramp state
    float setpoint;                    // Output: current tilt contribution (degrees)
}
```

---

## Interaction with BrakeTilt

`atr.setpoint` and `brake_tilt.setpoint` are **summed together** before being arbitrated against `torque_tilt.setpoint`. They are not independently arbitrated. This means BrakeTilt's downhill damping (which uses `atr.accel_diff`) reduces the combined terrain signal, not just BrakeTilt's own contribution.

See [[setpoint-composition|Setpoint Composition]] for the full arbitration logic.

---

## References

- [[atr.c]] — `atr_update()` lines 61–205; full algorithm
- [[atr.h]] — `ATR` struct lines 24–39
- [[motor-data|Motor Data]] — `MotorData.acceleration` (SMA-40) and `MotorData.filt_current` (Biquad)
- [[refloat-config|RefloatConfig]] — all `atr_*` fields at `datatypes.h:208–312`
- [[setpoint-composition|Setpoint Composition]] — how `atr.setpoint` is combined with other contributors
- [[brake-tilt|Brake Tilt]] — summed with ATR before arbitration
- [[torque-tilt|Torque Tilt]] — arbitrated against ATR+BrakeTilt sum
- [[tuning-atr|Tuning ATR]] — symptom-based tuning guide
