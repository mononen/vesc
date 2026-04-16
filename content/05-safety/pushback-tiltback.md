---
title: "Pushback and Tiltback System"
aliases:
  - "Pushback and Tiltback System"
tags:
  - safety
  - tiltback
  - pushback
  - speed
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/main.c
  - refloat/src/conf/datatypes.h
---

# Pushback and Tiltback System

Tiltbacks are graduated warnings delivered by physically tilting the board's nose. Rather than cutting power or stopping suddenly, Refloat moves the setpoint toward a tilt angle to push back against the rider's lean — signaling them to slow down or adjust behavior.

Tiltbacks are implemented in `calculate_setpoint_target()` (`main.c:492–706`), which runs every main loop cycle and sets the `SetpointAdjustmentType (SAT)` field of the [[state-machine|State Machine]].

---

## SAT Priority Hierarchy

Multiple tiltback conditions may be active simultaneously. Only the highest-priority active SAT is applied:

```
SAT_PB_TEMPERATURE    ← highest priority
SAT_PB_HIGH_VOLTAGE
SAT_PB_LOW_VOLTAGE
SAT_PB_SPEED
SAT_PB_DUTY           ← lowest priority
```

If temperature tiltback and duty tiltback are both active, temperature wins. Normal riding (`SAT_NONE`) is below all pushbacks.

When no pushback condition is active and the board is running, `SAT_CENTERING` applies briefly on startup (setpoint ramps to 0), then `SAT_NONE` takes over.

---

## How Tiltback Works

Each tiltback moves `setpoint_target` toward a configured angle:

```c
// Pseudocode for each SAT state
if tiltback_active:
    setpoint_target → tiltback_angle  (at tiltback_speed °/s)
else:
    setpoint_target → 0               (at tiltback_return_speed °/s)
```

The rate-limited movement means the tilt builds up gradually — riders feel the nose pushing back over 0.5–2 seconds rather than snapping instantly.

---

## Duty Cycle Tiltback (`SAT_PB_DUTY`)

```c
// main.c
if duty_cycle > tiltback_duty:
    SAT = SAT_PB_DUTY
    setpoint_target → tiltback_duty_angle at tiltback_duty_speed
```

Triggers when the motor's PWM duty cycle exceeds `tiltback_duty`. At 80–90% duty, the motor is near its voltage headroom limit — continuing to push harder risks not having enough voltage headroom for control.

The duty tiltback is the most common active warning during fast riding on flat ground.

**Beeper:** If `is_dutybeep_enabled`, the board continuously beeps while duty tiltback is active.

---

## Speed Tiltback (`SAT_PB_SPEED`)

```c
if speed_kph > tiltback_speed:
    SAT = SAT_PB_SPEED
    setpoint_target → tiltback_duty_angle at tiltback_duty_speed
```

Triggers above a configured speed, regardless of duty cycle. On descents where the motor is helping (low duty but high speed), duty tiltback may not trigger even at dangerous speeds — speed tiltback catches this case.

Speed and duty tiltback push to the same angle (`tiltback_duty_angle`) and at the same speed — they're distinguished only by their trigger condition.

---

## High Voltage Tiltback (`SAT_PB_HIGH_VOLTAGE`)

```c
if batt_voltage > tiltback_hv:
    // 500ms grace period before engaging
    if hv_timer > 0.5:
        SAT = SAT_PB_HIGH_VOLTAGE
        setpoint_target → tiltback_hv_angle at tiltback_hv_speed
```

Triggers when battery voltage exceeds `tiltback_hv`. This happens when braking into a full battery — regenerative current pushes voltage above the safe ceiling. The nose-up tilt reduces braking demand (less regen current), protecting the battery.

The 500ms grace period prevents triggering on transient voltage spikes.

**Beeper:** 5 audible beeps when HV tiltback activates.

---

## Low Voltage Tiltback (`SAT_PB_LOW_VOLTAGE`)

```c
if batt_voltage < tiltback_lv:
    // Voltage sag compensation: account for sag under load
    if persistent_low (not just sag):
        SAT = SAT_PB_LOW_VOLTAGE
        setpoint_target → tiltback_lv_angle at tiltback_lv_speed
```

Triggers on persistent low battery voltage. The firmware distinguishes between momentary voltage sag (normal under high current demand) and genuinely depleted voltage. This prevents false triggers during hard acceleration on a moderately charged battery.

**Beeper:** Continuous beeps while LV tiltback is active.

---

## Temperature Tiltback (`SAT_PB_TEMPERATURE`)

```c
if mosfet_temp > motor_config.l_temp_fet_start
   OR motor_temp > motor_config.l_temp_motor_start:
    SAT = SAT_PB_TEMPERATURE
    setpoint_target → tiltback_duty_angle at tiltback_duty_speed
```

The temperature limits are set in the BLDC layer (`l_temp_fet_start/end`, `l_temp_motor_start/end` in [[bldc-mc-configuration]]). When these thresholds are crossed, the BLDC layer begins current derating AND Refloat adds a tiltback. The combined effect is both reduced power and a rider warning.

---

## Return Speed

When a tiltback condition clears, the setpoint returns to 0:

```c
setpoint_target → 0  at tiltback_return_speed °/s
```

`tiltback_return_speed` controls how quickly the nose levels out after the condition clears. Slow return (2–4 °/s) = smooth leveling. Fast return (8–10 °/s) = abrupt return.

---

## Startup Centering — `SAT_CENTERING`

On initial engagement, `SAT = SAT_CENTERING` runs briefly:

```c
setpoint_target → 0  at startup_speed °/s
```

This ramps the setpoint from whatever angle the board was at engagement to 0 (level), smoothly. Once `setpoint_target` reaches 0, `SAT` transitions to `SAT_NONE`.

---

## References

- [[main.c]] — `calculate_setpoint_target()` lines 492–706, all SAT logic
- [[refloat-config|RefloatConfig]] — all `tiltback_*` fields at `datatypes.h:208–312`
- [[setpoint-composition|Setpoint Composition]] — `setpoint_target_interpolated` as base setpoint input
- [[state-machine|State Machine]] — SAT stored in `State.sat`
- [[bldc-mc-configuration]] — temperature limits triggering `SAT_PB_TEMPERATURE`
- [[nose-angling|Nose Angling and Pushback Speed Control]] — gradual speed angling vs urgent pushback
- [[tuning-tiltbacks|Tuning Tiltbacks and Pushback]] — practical configuration guide
