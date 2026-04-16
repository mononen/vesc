---
title: "Tuning ATR"
aliases:
  - "Tuning ATR"
tags:
  - tuning
  - atr
  - terrain
  - practical
  - ride-feel
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/atr.c
  - refloat/src/atr.h
  - refloat/src/motor_data.c
  - refloat/src/conf/datatypes.h
---

# Tuning ATR — Adaptive Terrain Response

[[atr|ATR — Adaptive Terrain Response]] is the most impactful ride-feel feature for real-world riding. It detects terrain resistance (hills, headwind, rough surface) by comparing how much acceleration the motor *should* produce for the current it's drawing versus how much it *actually* produces — then tilts the board to compensate.

When dialed in, the board feels like it intuitively handles hills and rough terrain. When misconfigured, it can oscillate, feel sluggish, or overreact at speed.

---

## The Core Idea

```
accel_diff = expected_acceleration - measured_acceleration

expected_acc = filtered_current / atr_amps_accel_ratio
measured_acc = SMA_40(ERPM_delta) / loop_hz
```

- **Positive `accel_diff`** (expected > measured): More current is being drawn than acceleration would justify → the terrain is resisting → tilt the nose up to help push through
- **Negative `accel_diff`** (measured > expected): More acceleration than the current justifies → the terrain is assisting (downhill) → tilt the nose down to maintain speed stability

This is elegant because it's terrain-agnostic: it doesn't care whether the resistance comes from a hill, headwind, or rough pavement — it just sees the physics and reacts.

---

## Parameters Reference

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `atr_strength_up` | 1–5 | Nose-up strength when resisting terrain (uphill/headwind) |
| `atr_strength_down` | 0.5–3 | Nose-down strength when assisting terrain (downhill) |
| `atr_threshold_up` | 0–5 | Minimum `accel_diff` to activate upward tilt |
| `atr_threshold_down` | 0–5 | Minimum `accel_diff` to activate downward tilt |
| `atr_on_speed` | 2–10 | Ramp speed engaging tilt (°/s) |
| `atr_off_speed` | 1–6 | Ramp speed disengaging tilt (°/s) |
| `atr_angle_limit` | 3–10 | Maximum ATR tilt angle (degrees) |
| `atr_speed_boost` | 0–2 | Extra multiplier at high speed (above 3000 ERPM) |
| `atr_response_boost` | 1–3 | Boost factor when direction reversal detected |
| `atr_transition_boost` | 1–2 | Extra speed on target reversal |
| `atr_filter` | 1–20 Hz | Low-pass cutoff on current before computing expected_acc |
| `atr_amps_accel_ratio` | 50–200 | Amps per unit acceleration (calibrates the model) |
| `atr_amps_decel_ratio` | 50–200 | Same but for decel/regen phase |

---

## Symptom-Based Tuning

### ATR feels like it does nothing on hills

**Cause:** `atr_strength_up/down` is too low, or `atr_threshold_up/down` is too high — the system is computing a small `accel_diff` but it never crosses the threshold, so the output is zero.

**Diagnosis:** If you have telemetry access, watch `atr.accel_diff` while climbing a moderate hill. If `accel_diff` is non-zero but `atr.setpoint` stays near zero, the threshold is the culprit.

**Fix:**
1. Lower `atr_threshold_up` (try 0.5, then 0.2, then 0.0 if still ineffective)
2. Increase `atr_strength_up` — start at 2.0, go to 3.0 if hills still feel unmanaged

---

### ATR oscillates or causes surging feel

**Cause:** `atr_on_speed` is too high, `atr_strength` is too high, or `atr_filter` is too low (reacting to noise). The tilt overshoots, the motor reacts, `accel_diff` reverses, the tilt reverses — cycle repeats.

**Fix (in order of preference):**
1. Reduce `atr_on_speed` — slower ramp prevents overshoot
2. Increase `atr_filter` cutoff frequency → lower Hz = smoother current signal → less noise-driven reaction
3. Reduce `atr_strength_up/down`
4. Increase `atr_threshold_up/down` slightly to filter out small oscillations

**Note:** Oscillation at low speed is often caused by the fast EMA filter (< 1000 ERPM). The code uses three EMA alpha bands — below 1000 ERPM it uses the slowest alpha. If you're oscillating while slowly maneuvering, this is expected behavior and threshold tuning is your lever.

---

### ATR feels too aggressive at speed

**Cause:** `atr_speed_boost` is multiplying the effect above 3000 ERPM and the correction becomes uncomfortably large at higher speeds.

**Fix:** Lower `atr_speed_boost`. Setting it to 0 disables the speed-dependent boost entirely, making ATR response the same at all speeds. You can also reduce `atr_strength_up/down` and rely on `atr_speed_boost` to restore the effect at speed (then reduce the boost).

---

### ATR is too slow to react on steep hills

**Cause:** `atr_on_speed` is too low (tilt ramps slowly), or `atr_response_boost` isn't engaging because the direction of tilt isn't reversing.

**Fix:**
1. Increase `atr_on_speed` — try 6–8 for aggressive terrain adaptation
2. Ensure `atr_response_boost` is set > 1.0 — this kicks in specifically when `accel_diff` reverses sign rapidly (e.g., cresting a hill)
3. Increase `atr_strength_up`

---

### Downhills feel uncontrolled or board accelerates too easily

**Cause:** `atr_strength_down` is too low — the board isn't tilting the nose down enough to signal the rider to brake.

**Fix:** Increase `atr_strength_down`. For very steep terrain, values of 2.5–4.0 are reasonable. The nose-down tilt makes the rider feel like the board is asking them to lean back and brake.

**Important:** `atr_strength_down` should generally be lower than `atr_strength_up`. Nose-down tilt on descents is intuitive but too much feels unstable.

---

### ATR seems correct at low speed but wrong at high speed (or vice versa)

**Cause:** The three EMA filter bands (by ERPM) use different smoothing alphas for `accel_diff`. At low ERPM, a slow filter is used to avoid reacting to low-speed noise. At high ERPM, a fast filter is used for quick terrain response.

**Diagnosis:** If ATR feels good at speed but wrong at low speed, the issue is typically in the `atr_threshold_*` values or `atr_on_speed` at low ERPM.

**Fix:** ATR is intentionally more conservative at low speed — this is by design. If low-speed behavior is the issue, re-examine `atr_threshold_up/down` and ensure you're not confusing ATR with [[torque-tilt|Torque Tilt]], which also activates based on current.

---

## Calibrating `atr_amps_accel_ratio`

This parameter defines how many amps the model expects per unit of measured acceleration. If it's wrong, ATR will always see a non-zero `accel_diff` even on flat ground — effectively adding a constant tilt offset.

**Symptom of wrong ratio:** On flat, level ground at constant speed, `atr.setpoint` drifts away from zero.

**Calibration procedure:**
1. Ride on flat level pavement at a steady moderate speed (around 3000–5000 ERPM)
2. Watch `atr.accel_diff` in telemetry
3. Adjust `atr_amps_accel_ratio` until `accel_diff` hovers near zero on flat ground
4. Similarly calibrate `atr_amps_decel_ratio` during steady-speed light braking

Starting point: `atr_amps_accel_ratio ≈ 100–150` for most wheel/motor combinations.

---

## `atr_filter` — The Current Smoothing Parameter

The raw motor current is noisy. Before computing `expected_accel`, the current signal is passed through a Biquad low-pass filter with cutoff at `atr_filter` Hz.

- **Lower `atr_filter` Hz** = smoother current → smoother `expected_accel` → less reactive ATR, less noise
- **Higher `atr_filter` Hz** = noisier current → more reactive ATR, faster terrain response but potentially oscillatory

Typical range: 3–10 Hz. Start at 5 Hz. If ATR is oscillating, drop to 3 Hz. If it's too sluggish, raise to 8–10 Hz.

---

## ATR and TorqueTilt Interaction

ATR and [[torque-tilt|Torque Tilt]] are **not** independent signals — they are arbitrated in [[setpoint-composition|Setpoint Composition]]:

```
combined_AB = atr.setpoint + brake_tilt.setpoint
if sign(combined_AB) == sign(torque_tilt.setpoint):
    use max(|combined_AB|, |torque_tilt|) * sign
else:
    use combined_AB + torque_tilt.setpoint
```

This means:
- If ATR and TorqueTilt agree (same direction), the larger of the two wins
- If they disagree (opposing directions), they add

Implication: if both ATR and TorqueTilt are strongly active in the same direction, you're not getting both — just the larger. Tuning one may reduce the apparent effect of the other. If you want both effects simultaneously, ensure they differ in direction (e.g., ATR up on a hill while TorqueTilt is up from acceleration — same direction, so max wins, effectively just ATR if ATR > TorqueTilt).

---

## References

- [[atr.c]] — `atr_update()` lines 61–205; full algorithm including speed bands, step sizes, response boost
- [[atr.h]] — `ATR` struct: `accel_diff`, `speed_boost`, `target`, `ramped_step_size`, `setpoint`
- [[refloat-config|RefloatConfig]] — all `atr_*` fields at `datatypes.h:208–312`
- [[motor-data|Motor Data]] — `MotorData.acceleration` (SMA-40), `MotorData.filt_current` (Biquad)
- [[setpoint-composition|Setpoint Composition]] — ATR+BrakeTilt vs TorqueTilt arbitration logic, `main.c:955–961`
- [[torque-tilt|Torque Tilt]] — arbitrated against ATR in setpoint composition
- [[brake-tilt|Brake Tilt]] — summed with ATR before arbitration
