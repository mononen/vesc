---
title: "Space Vector Modulation"
aliases:
  - "Space Vector Modulation"
tags:
  - motor
  - foc
  - pwm
  - svm
  - bldc
date: 2026-04-16
source_files:
  - bldc/motor/foc_math.c
  - bldc/motor/mcpwm_foc.c
---

# Space Vector Modulation (SVM)

Space Vector Modulation converts the two-phase voltage vector `(v_alpha, v_beta)` — produced by [[clarke-park-transforms|inverse Park]] after the [[current-pi-loop|Current PI Loop]] — into three PWM duty cycles for the motor's three half-bridge gates. It's the final step before electrical energy reaches the motor windings.

---

## Why Not Simple Sinusoidal PWM?

Sinusoidal PWM applies three independent sinusoidal duty cycles to each phase. Simple, but wastes ~13.4% of available DC bus voltage — the peak phase voltage achievable is only `V_bus / 2`.

SVM adds a zero-sequence (common-mode) offset that exploits the fact that only differential voltage between phases matters (not absolute voltage). This shifts all three duty cycles simultaneously, recovering the wasted headroom.

**SVM achieves:** Peak phase voltage = `V_bus / √3 ≈ 0.577 × V_bus`
**vs sinusoidal:** Peak phase voltage = `V_bus / 2 = 0.5 × V_bus`

That's a 15.5% increase in achievable torque for the same battery voltage and switching frequency. Critical for high-performance motor control.

---

## The Voltage Hexagon

All achievable voltage vectors form a hexagon in the (alpha, beta) plane:

```
         β
         |    Sector 2
    S3   |  /
         | /
─────────┼──────── α
  S4     |\  S1
         | \
    S5   |  Sector 6
         |
```

The hexagon has 6 sectors (0°–60° each). SVM determines which sector `(v_alpha, v_beta)` falls in, then synthesizes the vector using two adjacent active states plus two zero states.

---

## Algorithm

```c
// foc_math.c:245

// 1. Determine sector (0–5) from v_alpha, v_beta
sector = calculate_sector(v_alpha, v_beta)

// 2. Calculate time in each active vector (Volt-second balance)
t1 = (√3 * dt / V_bus) * (v_alpha * cos(sector*60°) + v_beta * sin(sector*60°))
t2 = (√3 * dt / V_bus) * (-v_alpha * sin(sector*60°) + v_beta * cos(sector*60°))
t0 = dt - t1 - t2    // Zero vector time

// 3. Compute duty cycles for each phase
(duty_A, duty_B, duty_C) = f(t1, t2, t0, sector)
```

The resulting duty cycles are between 0.0 and 1.0 and represent the fraction of the PWM period each high-side switch is on.

---

## PWM Timer Update

The duty cycles are written to the STM32 timer compare registers:

```c
// mcpwm_foc.c (TIMER_UPDATE_DUTY_M1 macro)
TIM1->CCR1 = (uint32_t)(duty_A * period);
TIM1->CCR2 = (uint32_t)(duty_B * period);
TIM1->CCR3 = (uint32_t)(duty_C * period);
```

These are center-aligned (up-down counting) PWM timers, which ensures symmetric switching and naturally avoids shoot-through without dead-time insertion in most configurations.

The timer update is atomic — all three channels update together at the timer period — ensuring no phase has a stale duty cycle relative to the others.

---

## Duty Cycle Limits

```c
// From mc_configuration:
l_max_duty = 0.95    // Maximum duty cycle (95%)
l_min_duty = 0.005   // Minimum non-zero duty (0.5%)
```

The maximum duty isn't 100% because at 100% duty, the high-side switch is on the entire PWM period — current sensing (which uses the low-side current shunt during the off-time) fails. A 5% off-time is maintained for current sampling.

Refloat's tiltbacks activate before this limit (typically at 75–90% duty) to provide rider warning before the firmware's hard ceiling.

---

## Overmodulation

When the commanded voltage vector falls outside the inscribed circle of the hexagon (but inside the hexagon boundary), "overmodulation" occurs. VESC handles this by clamping the duty cycles to valid ranges rather than scaling the vector down. This allows brief excursions beyond the linear SVM region during transients, at the cost of some harmonic distortion.

---

## `svm_sector` in Motor State

```c
// motor_state_t (foc_math.h)
uint8_t svm_sector;    // Current SVM sector (0–5)
```

The current sector is stored in the motor state struct and updated each ISR cycle. It's available in telemetry and can be used to verify correct motor operation (sectors should cycle 0–5 smoothly as the motor spins).

---

## References

- [[bldc/motor/foc_math.c]] — SVM implementation line 245
- [[bldc/motor/mcpwm_foc.c]] — PWM timer updates lines 2951–2952, 5000–5001
- [[foc-overview|FOC Overview]] — SVM in context of the full FOC chain
- [[clarke-park-transforms|Clarke and Park Transforms]] — inverse Park provides `(v_alpha, v_beta)` to SVM
- [[current-pi-loop|Current PI Loop]] — produces `(vd, vq)` → inverse Park → `(v_alpha, v_beta)` → SVM
- [[bldc-mc-configuration]] — `l_max_duty`, `l_min_duty` limits
