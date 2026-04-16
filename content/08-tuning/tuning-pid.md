---
title: "Tuning the PID Controller"
aliases:
  - "Tuning the PID Controller"
tags:
  - tuning
  - pid
  - practical
  - control
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/pid.c
  - refloat/src/pid.h
  - refloat/src/main.c
  - refloat/src/conf/datatypes.h
---

# Tuning the PID Controller

The [[pid-controller|PID Controller]] has three parameters that define the fundamental character of the ride — how stiff, how damped, and how self-correcting the board feels. Everything else (ATR, TorqueTilt, etc.) layers on top; getting the PID right first is essential.

---

## Mental Model Before Touching Anything

Think of the board as an inverted pendulum standing on one wheel. The controller's only job is to keep the wheel directly under the center of gravity. It does this by looking at the pitch angle and commanding motor current.

- **`kp`** — *Stiffness.* How hard the board pushes back when it's tilted. High `kp` = stiff and responsive. Low `kp` = loose and wallowy.
- **`kp2`** — *Damping.* How hard the board resists *changing* angle. High `kp2` = smooth and stable. Low `kp2` = snappy but prone to oscillation.
- **`ki`** — *Bias correction.* Slowly corrects for a persistent lean (e.g., rider is heavier on one foot, or the board is on a slope). This is a slow integrator — it should be small.

The tradeoff between `kp` and `kp2` is the core of PID feel. Think of `kp` as the spring and `kp2` as the shock absorber. A bike with a stiff spring but no damping will bounce. A bike with weak spring but strong damping will feel dead.

---

## Parameter Reference

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `kp` | 5–20 | Proportional gain on pitch error |
| `ki` | 0.01–0.08 | Integral gain; corrects steady-state lean |
| `ki_limit` | 0.1–1.5 | Maximum integral accumulation (0 = unlimited) |
| `kp2` | 5–25 | Gain on pitch rate (acts as derivative damping) |
| `kp_brake` | 0.5–1.0 | Multiplier on `kp` during deceleration |
| `kp2_brake` | 0.5–1.0 | Multiplier on `kp2` during deceleration |

---

## Symptom-Based Tuning

### The board feels loose, wallowy, or like it's fighting you slowly

**Cause:** `kp` is too low — not enough restoring force for the pitch error.

**Fix:** Increase `kp` by 1–2 at a time. Test by standing on the board and pushing the nose down sharply. A well-tuned `kp` snaps back firmly.

**Watch out for:** If you raise `kp` and it starts oscillating (buzzing under your feet), `kp2` needs to increase proportionally.

---

### The board oscillates or buzzes underfoot

**Cause:** `kp` is too high relative to `kp2` — the board overcorrects and oscillates. Classic underdamped system.

**Two fixes (try both):**
1. Reduce `kp` slightly.
2. Increase `kp2` — this is usually the better move, as it adds damping without losing stiffness.

**Diagnostic:** If the oscillation is a high-pitched buzz, the loop frequency (`hertz`) or Mahony KP is involved too. See [[tuning-mahony|Tuning the Mahony Filter]].

---

### The board consistently leans forward at cruising speed

**Cause:** `ki` is too low — the integrator isn't accumulating enough to correct the steady-state error, or `ki_limit` is capping it before it can.

**Fix:** Increase `ki` by 0.01 at a time. Also check `ki_limit` — if it's set very low (e.g., 0.1), the integrator physically cannot produce enough correction.

**Caution:** High `ki` causes sluggish recovery from large errors and can cause wind-up on steep hills. If the board feels like it "hunts" around level, `ki` is too high.

---

### The board nosedives when braking hard

**Cause:** `kp_brake` or `kp2_brake` is too low. When decelerating, the effective gains are `kp * kp_brake` and `kp2 * kp2_brake`. If these multipliers are small, the controller goes soft during braking — exactly when you need it most.

**Fix:** Increase `kp_brake` toward 1.0. Setting both brake multipliers to 1.0 means braking and accelerating feel identical — valid starting point. You can then lower `kp_brake` slightly if braking feels too harsh.

**Note:** Some riders deliberately lower `kp_brake` to 0.6–0.7 for a mellower braking feel. This is personal preference, not a safety concern, as long as you're not nosediving.

---

### The board feels too twitchy and snaps back too aggressively on bumps

**Cause:** `kp` too high, or [[mahony-ahrs-filter|Mahony AHRS Filter]] KP too high (angle estimate is too noisy). The board is reacting to high-frequency angle noise.

**Fix (two approaches):**
1. Lower `kp` slightly.
2. Lower `mahony_kp` — this smooths the angle estimate before the PID ever sees it. See [[tuning-mahony|Tuning the Mahony Filter]] for the tradeoffs.

---

### Engagement feels violent or the board kicks back on startup

**Cause:** The PID fires immediately at full gain the moment you engage. Check `startup_click_current` (haptic feedback) and the softstart ramp. The softstart ramps current at 100A/s in `main.c` — if your `kp` is very high, the first few cycles will command large current.

**Fix:** Lower `kp` slightly, or tune the engagement flow via startup tolerances. See [[tuning-engagement|Tuning Engagement and Startup]].

---

## Brake Scaling in Depth

When `dir_current < 0` and `abs_erpm > 500` (braking), the PID multiplies its gains:

```
effective_kp  = kp  * kp_brake_scale.ema
effective_kp2 = kp2 * kp2_brake_scale.ema
```

The scale transitions smoothly via a 1 Hz EMA — it doesn't snap between full gain and brake gain. This means:
- Entering a braking phase: gains ramp **down** over ~1 second
- Leaving a braking phase: gains ramp **back up** over ~1 second

This is why the board may feel briefly soft right after hard braking — the gains are ramping back. If you find this annoying, set `kp_brake` and `kp2_brake` both to 1.0 to eliminate the difference entirely.

---

## `ki_limit` and Integrator Wind-Up

The `ki_limit` parameter caps the maximum value the I term can reach. Without a limit (`ki_limit = 0`), the integrator can accumulate indefinitely on a persistent error — such as a long uphill. When the hill ends, the over-wound integrator will push the board forward for a moment before unwinding.

A `ki_limit` of around 0.5–1.0 A is a good starting point. Too tight and `ki` has no effect; too loose and you get the wind-up behavior.

---

## Interaction with the Mahony Filter

The PID receives `balance_pitch` from Refloat's own [[mahony-ahrs-filter|Mahony AHRS Filter]]. If `mahony_kp` is high, the angle estimate reacts quickly but is noisier — your `kp` is amplifying that noise. If `mahony_kp` is low, the angle estimate is smooth but lags real angle changes — your `kp2` becomes more critical because pitch rate is the only fast signal left.

A useful mental model:
- High Mahony KP + moderate `kp` + high `kp2` = responsive, stable
- Low Mahony KP + high `kp` + moderate `kp2` = smooth but requires more damping to prevent lag-induced oscillation

---

## Suggested Starting Points

**Mellow street riding:**
```
kp = 9, ki = 0.03, kp2 = 12, ki_limit = 0.5
kp_brake = 0.75, kp2_brake = 0.75
```

**Aggressive/sporty:**
```
kp = 14, ki = 0.04, kp2 = 18, ki_limit = 0.8
kp_brake = 0.85, kp2_brake = 0.85
```

These are starting points only. Motor winding resistance, rider weight, and wheel size all affect what "feels right."

---

## References

- [[pid.c]] — `pid_control()` lines 51–89, the full control law
- [[pid.h]] — `PID` struct fields: `p`, `i`, `rate_p`, scale EMAs
- [[main.c]] — `pid_control()` called in `imu_ref_callback`, lines 724–763
- [[refloat-config|RefloatConfig]] — `kp`, `ki`, `kp2`, `ki_limit`, `kp_brake`, `kp2_brake`
- [[mahony-ahrs-filter|Mahony AHRS Filter]] — produces `balance_pitch` and `pitch_rate` consumed by PID
- [[setpoint-composition|Setpoint Composition]] — the `setpoint` that PID error is computed against
- [[tuning-mahony|Tuning the Mahony Filter]] — filter dynamics that affect PID noise input
