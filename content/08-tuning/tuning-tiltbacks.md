---
title: "Tuning Tiltbacks and Pushback"
aliases:
  - "Tuning Tiltbacks and Pushback"
tags:
  - tuning
  - tiltback
  - pushback
  - safety
  - speed
  - practical
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/main.c
  - refloat/src/conf/datatypes.h
---

# Tuning Tiltbacks and Pushback

Tiltbacks are Refloat's graduated speed-limiting system — instead of abruptly cutting power when you approach a limit, the board tilts its nose back to signal the rider to slow down. Understanding and tuning each tiltback type is important both for safety and ride comfort.

See [[pushback-tiltback|Pushback and Tiltback System]] for the full technical explanation.

---

## The Tiltback Hierarchy

Tiltbacks are ranked by priority (`SetpointAdjustmentType`, or SAT). Higher-priority tiltbacks override lower-priority ones:

```
SAT_PB_TEMPERATURE  (highest priority)
SAT_PB_HIGH_VOLTAGE
SAT_PB_LOW_VOLTAGE
SAT_PB_SPEED
SAT_PB_DUTY         (lowest priority)
```

If temperature protection kicks in while you're at speed, temperature tiltback wins and overrides speed tiltback. All tiltback types share the same underlying mechanism: the setpoint target moves to a configured angle at a configured rate.

---

## Duty Cycle Tiltback

Duty cycle tiltback is the first warning that you're approaching the motor's power limit. Duty cycle represents how much of the available battery voltage the motor is using — at 100% duty, there's no more headroom.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `tiltback_duty` | 0.70–0.90 | Duty cycle threshold to trigger tiltback (0.0–1.0) |
| `tiltback_duty_angle` | 3–10° | Nose angle at full tiltback |
| `tiltback_duty_speed` | 5–20 °/s | How fast the nose tilts back |

### Tuning Guidance

**Setting `tiltback_duty`:** This is your early-warning threshold. 0.75–0.80 is common — it leaves ~20–25% headroom above the tiltback trigger. Setting it too high (0.90+) means you're almost at the hard cutoff before tiltback begins. Setting it too low (0.65) means the board is constantly nosing back at moderate speeds.

**Setting `tiltback_duty_angle`:** This is how strongly the board pushes back. A 5° nose-up is noticeable but not alarming. 8–10° is aggressive — hard to ignore. Most riders find 5–7° effective without being unpleasant.

**Setting `tiltback_duty_speed`:** How fast the tilt engages. Slow speeds (5–8 °/s) give a gentle warning that builds over time. Fast speeds (15–20 °/s) are urgent and immediately noticeable. For safety, faster is generally better — the warning should be felt before the limit is reached. Slower is more comfortable for experienced riders who are aware of their limits.

### The Duty Beep

If `is_dutybeep_enabled` is true, the board continuously beeps while duty tiltback is active. This is an additional sensory warning on top of the nose tilt. Useful if the nose tilt is subtle.

---

## Speed Tiltback

Speed tiltback triggers above a configurable speed threshold, independent of duty cycle. On flat ground, you'll hit duty tiltback before speed tiltback, but on downhills where the motor is helping rather than fighting, ERPM can increase without high duty — this is where speed tiltback matters.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `tiltback_speed` | 20–50 km/h | Speed threshold to begin tiltback |

Speed tiltback uses the same angle and speed as duty tiltback (`tiltback_duty_angle`, `tiltback_duty_speed`). There's only one tiltback angle — both duty and speed push to the same target.

### Tuning Guidance

Set `tiltback_speed` to the maximum speed you're comfortable riding. The tiltback doesn't cut power — it pushes the nose back and asks you to shift your weight rearward (naturally causing braking). If you're willing to override it and keep pushing forward, you can, but you're approaching the firmware's hard limits.

---

## Variable (Noseangling) and Constant Tiltback

These are separate from the duty/speed tiltback — they create a gradual speed-dependent nose angle that increases as you go faster, giving the board a natural lean-limiting feel rather than a sudden nose-snap.

See [[nose-angling|Nose Angling and Pushback Speed Control]] for the full algorithm.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `tiltback_variable` | 0–0.0005 | Degrees per ERPM above threshold |
| `tiltback_variable_erpm` | 1000–5000 | ERPM where variable tiltback begins |
| `tiltback_variable_max` | 0–5° | Maximum angle from variable tiltback |
| `tiltback_constant` | 0–5° | Fixed nose angle above `constant_erpm` |
| `tiltback_constant_erpm` | 3000–8000 | ERPM threshold for constant tiltback |
| `noseangling_speed` | 1–10 °/s | Rate at which noseangling ramps |

### Tuning Guidance

**Variable tiltback** creates a smooth, progressive nose angle that builds with speed. This is the "cruise control" feeling — as you go faster, the board ever-so-gently asks you to slow down. Riders who want a natural speed cap without harsh pushback prefer higher `tiltback_variable` values.

**Constant tiltback** adds a fixed nose-up at a specific ERPM. This creates a distinct "step" in the board feel above the threshold — useful as an additional clear signal that you've crossed a certain speed.

**`noseangling_speed`** controls how quickly the nose angle changes as ERPM changes. A low value (1–3 °/s) means the nose trails well behind actual speed changes — gentle but slow. High values (8–10 °/s) track speed more closely.

---

## High Voltage Tiltback

When battery voltage is high (e.g., freshly charged), regenerative braking can push voltage above the battery's safe ceiling. The firmware monitors battery voltage and triggers a tiltback if it exceeds `tiltback_hv`.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `tiltback_hv` | 58–67 V (for 60V systems) | Voltage threshold |
| `tiltback_hv_angle` | 5–15° | Nose angle at high voltage tiltback |
| `tiltback_hv_speed` | 5–20 °/s | Ramp speed |

### Tuning Guidance

**`tiltback_hv`** should be set slightly below your battery's absolute maximum voltage. For a 20S pack (16.8V per cell fully charged → ~67V max), setting `tiltback_hv` around 65V gives a small safety margin.

**Why this matters:** If you're fully charged and begin a long downhill, regen braking sends current back to the battery. If the battery is already full, it can't absorb it — voltage spikes dangerously. The tiltback nose-up reduces braking current demand, reducing regen.

**500ms grace period:** The firmware waits 500ms after exceeding the threshold before engaging HV tiltback. This filters out momentary voltage spikes. If your battery's BMS has its own protection, this may be redundant, but it's a good belt-and-suspenders safety feature.

**The beep pattern:** When HV tiltback engages, the board beeps five times. If you hear this unexpectedly, you're likely braking hard on a full charge.

---

## Low Voltage Tiltback

Low voltage tiltback warns when battery is depleting. It's aware of *voltage sag* under load — the transient voltage drop when the motor draws high current. The firmware only triggers LV tiltback if the low voltage persists, not if it's just momentary sag.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `tiltback_lv` | 40–50 V (for 60V systems) | Voltage threshold |
| `tiltback_lv_angle` | 5–10° | Nose angle at low voltage tiltback |
| `tiltback_lv_speed` | 5–20 °/s | Ramp speed |

### Tuning Guidance

**`tiltback_lv`** sets your low-battery warning point. Consider your BMS cutoff voltage and work backward — you want the tiltback to engage comfortably before the BMS can shut off mid-ride.

**Voltage sag awareness:** Setting `tiltback_lv` too high (e.g., same as nominal voltage) will cause constant false triggers because motor current always causes some sag. Refloat handles this with a voltage-sag-aware comparison, but the threshold should still be below your expected loaded voltage.

**Audible warning:** LV tiltback also triggers beeps. The startup routine also announces battery level (number of beeps) if `is_beeper_enabled` is set.

---

## Temperature Tiltback

If MOSFET or motor temperature exceeds configured limits, the board tilts back to reduce power demand.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `mc_configuration.l_temp_fet_start` | 70–85°C | FET temp where derating begins |
| `mc_configuration.l_temp_fet_end` | 85–95°C | FET temp where current is fully cut |
| `mc_configuration.l_temp_motor_start` | 80–100°C | Motor temp where derating begins |
| `mc_configuration.l_temp_motor_end` | 100–110°C | Motor temp where current is fully cut |

Temperature tiltback in Refloat activates when the temperature-based current derating in [[bldc-mc-configuration]] kicks in. The BLDC firmware itself progressively reduces max current as temperature rises — Refloat detects this and adds a nose tiltback on top.

### Tuning Guidance

Temperature limits are primarily set in `mc_configuration` (in the BLDC layer), not in `RefloatConfig`. The BLDC firmware handles the actual current derating. Refloat's temperature tiltback is an additive behavioral response.

If you're hitting temperature tiltback frequently:
1. Check airflow around the controller — VESC is typically mounted on the board
2. Reduce `l_current_max` in `mc_configuration` — lower peak current = less heat
3. Check motor winding resistance and ensure FOC parameters are accurate — incorrect motor parameters lead to higher-than-necessary currents

---

## Return Speed

After a tiltback condition clears (speed drops, duty drops, voltage normalizes), the nose returns to neutral. `tiltback_return_speed` controls this.

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `tiltback_return_speed` | 1–10 °/s | Rate to return nose to neutral after tiltback |

**Tuning:** A slow return (2–4 °/s) means the board gradually straightens out as you slow down — smooth and comfortable. A fast return (8–10 °/s) means the nose snaps back quickly, which can feel abrupt. Most riders prefer 3–5 °/s.

---

## References

- [[main.c]] — `calculate_setpoint_target()` lines 492–706, all tiltback SAT logic
- [[refloat-config|RefloatConfig]] — all `tiltback_*` fields at `datatypes.h:208–312`
- [[pushback-tiltback|Pushback and Tiltback System]] — technical explanation of SAT hierarchy and setpoint calculation
- [[nose-angling|Nose Angling and Pushback Speed Control]] — variable/constant tiltback detail
- [[bldc-mc-configuration]] — temperature and current limits in `mc_configuration`
- [[state-machine|State Machine]] — SAT is a field of `State`, set by `calculate_setpoint_target()`
