---
title: "FOC Overview"
aliases:
  - "FOC Overview"
  - "FOC"
  - "Field Oriented Control"
tags:
  - motor
  - foc
  - bldc
  - overview
date: 2026-04-16
source_files:
  - bldc/motor/mcpwm_foc.c
  - bldc/motor/foc_math.h
---

# FOC Overview — Field-Oriented Control

Field-Oriented Control (FOC) is the motor control strategy used by VESC to drive the BLDC/PMSM motor. It provides smooth, efficient torque control at any speed — from standstill to maximum velocity — by continuously controlling the motor's current in a rotating reference frame that tracks the rotor position.

For the onewheel use case: Refloat commands a current value; FOC executes that command at the hardware level 20,000 times per second.

---

## Why Not Just Apply Voltage?

A BLDC motor has three phases. The phases are wound coils — at any given moment, only certain current combinations produce torque in the right direction. The optimal currents change as the rotor rotates (every 60°, a different pair of coils is most effective).

Naive square-wave commutation ("trapezoidal") switches phases at fixed rotor positions and produces torque ripple — the output torque varies with rotor angle. This is felt as vibration, especially at low speeds.

FOC eliminates torque ripple by continuously calculating and applying the optimal current vector for the current rotor position. The result is smooth, consistent torque at any rotor angle.

---

## The Three-Step Conversion

FOC converts between three reference frames:

```
Three-phase (A, B, C)         Rotating field
rotating AC currents      →   looks like DC
                              (d-axis, q-axis)
                                    ↓
                              PI control here
                                    ↓
Three-phase (A, B, C)         Rotating field
PWM duty cycles        ←      voltages to apply
```

**Step 1 — Forward path:** [[clarke-park-transforms|Clarke and Park Transforms]]
- Clarke: (ia, ib, ic) → (i_alpha, i_beta) — 3-phase to 2-phase stationary
- Park: (i_alpha, i_beta, θ) → (id, iq) — stationary to rotating (rotor frame)

**Step 2 — Control:** [[current-pi-loop|Current PI Loop]]
- id PI: drives id → 0 (no flux weakening needed for basic operation)
- iq PI: drives iq → commanded torque current

**Step 3 — Inverse path:**
- Inverse Park: (vd, vq, θ) → (v_alpha, v_beta)
- [[space-vector-modulation|Space Vector Modulation]]: (v_alpha, v_beta) → (duty_A, duty_B, duty_C) → PWM timers

---

## Id and Iq — The Key Variables

In the rotor-aligned reference frame:

**Id — Direct-axis current (flux):** Aligned with the rotor's permanent magnet flux. At zero, no additional flux is created — the permanent magnets handle it. Positive Id creates field weakening (allows higher speeds). Negative Id is inefficient and avoided.

**Iq — Quadrature-axis current (torque):** Perpendicular to Id. All motor torque is proportional to Iq. This is what Refloat actually controls.

When Refloat calls `VESC_IF->mc_set_current(I)`, it's setting the Iq target. The FOC loop maintains Id ≈ 0 and drives Iq to the commanded value.

Motor torque = K_t × Iq (approximately), where K_t is the motor torque constant.

---

## The 20 kHz ISR Loop

The entire FOC computation runs inside `mcpwm_foc_adc_int_handler()` at 20 kHz (once per PWM cycle):

```
ADC interrupt (every 50 µs):
  1. Read phase currents (ADC)
  2. Read battery voltage (ADC)
  3. Clarke transform
  4. Update rotor angle estimate (observer or encoder)
  5. Park transform
  6. PI control (Id, Iq)
  7. Decoupling feedforward
  8. Inverse Park
  9. SVM
  10. Write PWM timer registers
```

Total ISR duration: ~30–50 µs. This leaves some headroom before the next interrupt.

---

## Rotor Position — The Critical Input

The Park transform requires knowing the rotor's electrical angle θ. This comes from one of:

**Encoder (if equipped):** Absolute position sensor directly attached to motor shaft. Most accurate.

**Hall sensors:** 6 discrete positions per electrical revolution. Lower resolution, but simple and robust. Common on hub motors.

**Sensorless observer:** Software estimates θ from back-EMF using a flux observer. Works above a minimum speed (set by `foc_sl_erpm`). At low speed/standstill, switches to HFI (High Frequency Injection).

For most onewheel hub motors, the motor starts sensorless or with Hall sensors. The sensorless observer (`foc_observer_update()`) runs continuously to refine the angle estimate.

---

## Motor Parameters Required

FOC requires accurate knowledge of the motor's electrical characteristics. These are in [[bldc-mc-configuration]]:

- `foc_motor_r` — Stator resistance (Ω): needed for voltage feedforward
- `foc_motor_l` — Stator inductance (H): determines PI gains via bandwidth calculation
- `foc_motor_flux_linkage` — Permanent magnet flux (Wb): relates Iq to torque

Incorrect motor parameters cause control instability, excess heat, or poor torque tracking. The VESC Tool's motor detection procedure measures these automatically.

---

## What Refloat Controls vs What FOC Controls

| Layer | Controls | Frequency |
|-------|----------|-----------|
| Refloat (balance) | Iq target (motor current = torque) | ~20–30 kHz (via callback) |
| FOC (BLDC) | Id, Iq actual currents | 20 kHz |
| FOC (BLDC) | Phase voltages (vd, vq) | 20 kHz |
| FOC (BLDC) | PWM duty cycles | 20 kHz |
| Physical motor | Rotor torque, speed | Continuous |

Refloat thinks in terms of current (amps). FOC thinks in terms of voltage vectors. The hardware thinks in terms of switching duty cycles. FOC bridges all three levels transparently.

---

## References

- [[bldc/motor/mcpwm_foc.c]] — `mcpwm_foc_adc_int_handler()` line 2848, `control_current()` line 4550
- [[bldc/motor/foc_math.h]] — `motor_state_t` lines 26–66, `motor_all_state_t` lines 138–248
- [[clarke-park-transforms|Clarke and Park Transforms]] — coordinate transform mathematics
- [[current-pi-loop|Current PI Loop]] — Id/Iq PI control with decoupling
- [[space-vector-modulation|Space Vector Modulation]] — SVM from voltage vector to PWM duties
- [[bldc-mc-configuration]] — motor parameters and current limits
- [[refloat-bldc-interface|Refloat–BLDC Interface]] — how Refloat's current command enters this loop
