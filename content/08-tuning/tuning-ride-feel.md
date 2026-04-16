---
title: "Tuning Ride Feel"
aliases:
  - "Tuning Ride Feel"
tags:
  - tuning
  - ride-feel
  - torque-tilt
  - brake-tilt
  - turn-tilt
  - booster
  - practical
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/torque_tilt.c
  - refloat/src/brake_tilt.c
  - refloat/src/turn_tilt.c
  - refloat/src/booster.c
  - refloat/src/conf/datatypes.h
---

# Tuning Ride Feel — TorqueTilt, BrakeTilt, TurnTilt, Booster

These four algorithms shape the *character* of the ride on top of the baseline [[pid-controller|PID Controller]]. Unlike [[atr|ATR — Adaptive Terrain Response]], which responds to terrain, these respond to the rider's own inputs — acceleration, braking, turning, and large lean angles.

Tune them **one at a time** after the PID and ATR are stable.

---

## TorqueTilt

[[torque-tilt|Torque Tilt]] tilts the nose in proportion to filtered motor current. Accelerating hard → nose rises. Braking hard → nose drops (or tail rises). This mimics how a human-powered vehicle behaves and makes the board feel more alive and feedback-rich.

### Parameters

| Parameter                   | Typical Range | Effect                                               |
| --------------------------- | ------------- | ---------------------------------------------------- |
| `torquetilt_start_current`  | 5–20 A        | Current threshold below which TorqueTilt is inactive |
| `torquetilt_strength`       | 0.05–0.25     | Degrees of tilt per amp above threshold              |
| `torquetilt_strength_regen` | 0.02–0.15     | Same but during regenerative braking                 |
| `torquetilt_on_speed`       | 5–30 °/s      | How fast the tilt ramps up                           |
| `torquetilt_off_speed`      | 2–15 °/s      | How fast the tilt returns to zero                    |
| `torquetilt_angle_limit`    | 3–8°          | Maximum TorqueTilt angle                             |

### Symptom-Based Tuning

**Board feels dead / no acceleration feedback:**
Increase `torquetilt_strength` from 0 upward in steps of 0.05. The first noticeable effect is that the nose noticeably rises when you accelerate hard — this is the "alive" feeling.

**TorqueTilt causes oscillation at low speed:**
Two causes:
1. `torquetilt_on_speed` too high — the tilt overshoots and the PID corrects, which changes the current, which changes TorqueTilt — feedback loop. Lower `on_speed` to 5–8 °/s.
2. `torquetilt_start_current` too low — small current fluctuations are triggering TorqueTilt. Raise the threshold so it only fires on actual acceleration.

**Tilt lingers too long after acceleration:**
Lower `torquetilt_off_speed`. This controls how fast the tilt returns to baseline. A value of 4–6 °/s gives a natural decay. Very low values (1–2 °/s) feel like the board "sticks" in the tilted position.

**Braking feel is weird / asymmetric:**
`torquetilt_strength_regen` controls the braking behavior separately. If braking nosedive feels too strong, lower it. If braking feels mushy, increase it. Setting it to zero disables TorqueTilt during braking while keeping it active during acceleration.

**Nose rises too much at full acceleration:**
Lower `torquetilt_angle_limit`. This hard-caps the maximum tilt regardless of current. Most riders find 5–6° feels natural; beyond 8° starts to feel like the board is pushing you backward.

### Interaction with ATR

TorqueTilt is arbitrated against ATR+BrakeTilt in [[setpoint-composition|Setpoint Composition]]. On a hill with heavy acceleration, both ATR and TorqueTilt may want to tilt the nose up — but only the larger of the two wins. This means on uphill acceleration, TorqueTilt often "loses" to ATR. Consider whether you need both at similar strengths, or if one is sufficient.

---

## BrakeTilt

[[brake-tilt|Brake Tilt]] lifts the nose slightly during active braking. The goal is to provide a natural deceleration feel — the nose rising slightly tells the rider "you're slowing down, shift weight back."

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `braketilt_strength` | 5–25 | Higher = more nose lift during braking |
| `braketilt_lingering` | 0–20 | How long (in ms-ish cycles) the nose-lift persists after braking ends |

### How Strength Maps to Angle

The factor is not a direct angle value. Internally:
```
factor = -(0.5 + (20 - strength) / 5)
```

At `strength = 10`: `factor ≈ -2.5`  
At `strength = 20`: `factor ≈ -0.5`  
At `strength = 5`: `factor ≈ -3.5`

A larger negative factor means a smaller nose-lift angle (confusingly, higher "strength" = smaller factor magnitude). The actual setpoint contribution is `factor * balance_offset / some_divisor` — it's relative to the board's balance offset, not a fixed angle.

**Practical upshot:** Experiment in steps of 5 on `braketilt_strength`. Most riders find 10–18 feels natural.

### Downhill Braking Damping

BrakeTilt has built-in downhill damping: if `atr.accel_diff` is strongly negative (the terrain is assisting — i.e., a steep downhill), BrakeTilt's effect is reduced or zeroed. This prevents double-correction on descents where ATR is already tilting the nose down.

**Symptom:** BrakeTilt feels weak on flat ground but seems to work on hills. This is the opposite of the damping — if ATR is pushing nose-down, BrakeTilt's nose-up is fighting it. Check `atr.setpoint` and `brake_tilt.setpoint` in telemetry to see if they're opposing each other.

### Lingering

`braketilt_lingering` keeps the nose-up effect active for a period after braking ends. This smooths the transition back to flat riding. Too much lingering can make the board feel like it's in a constant slight nose-up even at cruising speed.

---

## TurnTilt

[[turn-tilt|Turn Tilt]] tilts the nose when the board is turning (detected via yaw rate). It serves two purposes:
1. Prevents corner nosedive — in a sharp turn, the board is decelerating relative to straight-line travel, so the nose tends to drop. TurnTilt compensates.
2. Makes carving feel more intuitive — the board leans into turns.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `turntilt_strength` | 0.02–0.15 | Degrees of nose tilt per aggregate yaw degree |
| `turntilt_angle_limit` | 2–8° | Maximum TurnTilt angle |
| `turntilt_start_angle` | 5–30° | Minimum yaw aggregate to activate |
| `turntilt_start_erpm` | 500–2000 | Minimum speed to activate |
| `turntilt_speed` | 5–25 °/s | Ramp speed for tilt |
| `turntilt_erpm_boost` | 500–3000 | ERPM where speed boost starts applying |
| `turntilt_erpm_boost_end` | 3000–10000 | ERPM where speed boost reaches maximum |
| `turntilt_yaw_aggregate` | 50–200 ms | Time window for yaw accumulation |

### Symptom-Based Tuning

**Corners feel like the nose dips when carving:**
This is the problem TurnTilt solves. Increase `turntilt_strength` in steps of 0.02. You want to see the nose hold stable or lift slightly in a carve, not drop.

**TurnTilt triggers on straight rough pavement:**
Reduce `turntilt_start_angle` — the yaw aggregate threshold is too low and road vibration is being read as turning. Start at 15–20°.

**TurnTilt activates too slow:**
Increase `turntilt_speed` (the ramp rate). Also check `turntilt_yaw_aggregate` — a longer window accumulates more yaw before triggering, which adds latency.

**TurnTilt at speed feels too aggressive:**
At high speed, the `erpm_boost` applies extra multiplier to TurnTilt effect. Reduce `turntilt_erpm_boost` or lower `turntilt_strength` and let the boost provide the high-speed amplification you want.

**Board doesn't recover from turns smoothly:**
This is a ramp-down issue. TurnTilt decays at `turntilt_speed` when the yaw aggregate returns to zero. If it snaps back, lower the speed. The `turntilt_start_angle` threshold means it deactivates completely below that aggregate angle, which can cause an abrupt step-off.

### Yaw Aggregate Explained

TurnTilt doesn't respond to instantaneous yaw rate — it accumulates yaw change over `turntilt_yaw_aggregate` milliseconds. This makes it immune to momentary road-induced yaw spikes. When the accumulated yaw exceeds `turntilt_start_angle`, TurnTilt activates. The accumulated yaw then tracks ongoing turning and decays when the turn straightens out.

Setting `turntilt_yaw_aggregate` too long makes TurnTilt very slow to activate on quick chicanes. Too short and single bumps may trigger it.

---

## Booster

[[Booster]] injects additional motor current (bypassing the normal setpoint path) when the proportional pitch error exceeds a threshold. It's a nonlinear stiffener — the board feels normal in small deviations, then adds a firm "wall" when the lean gets large.

Unlike the PID's P term, Booster is calculated from the raw pitch angle, not `balance_pitch`. This means it can act even before the Mahony filter fully responds.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `booster_angle` | 3–10° | Pitch error threshold before boost activates |
| `booster_ramp` | 50–500 A/s | How fast boost current ramps up |
| `booster_current` | 2–10 A | Maximum additional current from booster |
| `brkbooster_angle` | 3–10° | Same but for braking direction |
| `brkbooster_ramp` | 50–500 A/s | Ramp for braking booster |
| `brkbooster_current` | 2–10 A | Max braking booster current |

### Symptom-Based Tuning

**Board feels like it "gives up" when leaned hard:**
The PID P term is proportional — it provides linearly more force per degree of error. If it's not enough at large angles, the Booster provides a nonlinear top-up. Increase `booster_current` and/or lower `booster_angle` (activates at smaller errors).

**Booster feels like a sudden jolt when hitting its threshold:**
`booster_angle` is set too low — the transition into boost territory is abrupt. Raise `booster_angle` to push the threshold further away from normal operation. Alternatively, lower `booster_ramp` so the boost ramps in more gradually.

**Nose diving during hard braking despite other tuning:**
Engage `brkbooster_current`. Set `brkbooster_angle` to activate at moderate braking lean (around 5°). This is separate from the forward booster and specifically addresses braking nosedives at the limits.

**Booster causes buzzing/oscillation:**
`booster_angle` is too low (activating on normal angle noise) or `booster_ramp` too fast. Raise `booster_angle` by 1–2° and halve `booster_ramp`. The 1 Hz EMA smoothing on booster current helps, but if the threshold is inside normal riding variance, it will still oscillate.

### How Booster Fits Into the Output

The booster adds directly to the PID output after the PID current is computed:

```
new_current = (pid.p + pid.i + pid.rate_p + booster_current) * softstart_limit
```

This means booster current and PID current share the same `current_max/min` clamp. If the motor is already at its current limit from PID, booster current is effectively clipped — the limit is absolute.

---

## Tuning Order and Interactions

These four algorithms interact with each other and with ATR. Recommended order:

1. **Zero all secondary algorithms first.** Set `torquetilt_strength = 0`, `braketilt_strength = 0`, `turntilt_strength = 0`, `booster_current = 0`. Tune PID and ATR until baseline is stable.

2. **Enable TorqueTilt.** It's the most ride-feel-affecting. Get a strength you like on flat ground first.

3. **Enable BrakeTilt.** Test with short sharp brakes. Dial `braketilt_strength` until braking feels natural.

4. **Enable TurnTilt.** Find a smooth surface for carving. Raise strength until corners feel stable.

5. **Enable Booster last.** Only needed if the board still feels like it "lets go" at the limits after everything else is tuned.

At each step, return to the previous step's test to verify you haven't disrupted it.

---

## References

- [[torque_tilt.c]] — `torque_tilt_update()`, target calculation and ramp logic, lines 41–78
- [[brake_tilt.c]] — `brake_tilt_update()`, downhill damping logic, lines 45–88
- [[turn_tilt.c]] — `turn_tilt_update()`, yaw aggregate and speed boost, lines 48–120
- [[booster.c]] — `booster_update()`, threshold and EMA logic, lines 37–80
- [[refloat-config|RefloatConfig]] — all `torquetilt_*`, `braketilt_*`, `turntilt_*`, `booster_*` fields
- [[setpoint-composition|Setpoint Composition]] — how TorqueTilt is arbitrated against ATR+BrakeTilt
- [[pid-controller|PID Controller]] — booster current added to PID output before motor command
- [[atr|ATR — Adaptive Terrain Response]] — arbitrated against TorqueTilt; understand interaction before tuning strengths
