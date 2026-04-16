---
title: "Clarke and Park Transforms"
aliases:
  - "Clarke and Park Transforms"
tags:
  - motor
  - foc
  - math
  - transforms
  - bldc
date: 2026-04-16
source_files:
  - bldc/motor/mcpwm_foc.c
  - bldc/motor/foc_math.c
---

# Clarke and Park Transforms

Two sequential coordinate transforms convert three-phase motor currents into a rotating reference frame where they can be controlled with simple PI loops. Together they form the backbone of [[foc-overview|FOC Overview]].

---

## The Problem They Solve

A three-phase motor has three sinusoidal currents (ia, ib, ic) that are 120° apart in phase. As the rotor spins, the optimal current direction rotates with it. Controlling three correlated AC quantities is complex.

The transforms convert these into two DC quantities (id, iq) in a frame that rotates with the rotor — where "DC" means they're constant when the motor is spinning at constant speed. DC quantities are easy to control with ordinary PI loops.

---

## Step 1: Clarke Transform (3-Phase → 2-Phase Stationary)

Reduces three correlated signals to two orthogonal signals in a fixed (stator-referenced) frame.

**With three current sensors (full Clarke):**
```
i_alpha = (2/3) * ia - (1/3) * ib - (1/3) * ic
i_beta  = (1/√3) * (ib - ic)
```

**With two current sensors (balanced Clarke — assumes ia + ib + ic = 0):**
```
i_alpha = ia
i_beta  = (ia + 2*ib) / √3
```

VESC typically uses two shunt resistors (measuring ia and ib), so the balanced form is used.

**Code location:** `mcpwm_foc.c:3271–3279`

**Result:** `(i_alpha, i_beta)` — two orthogonal current components in the stationary stator frame. These rotate at the motor's electrical frequency.

---

## Step 2: Park Transform (Stationary → Rotating Rotor Frame)

Rotates the stationary (i_alpha, i_beta) vector by the negative of the rotor's electrical angle θ, producing quantities fixed to the rotor:

```
id = cos(θ) * i_alpha + sin(θ) * i_beta
iq = cos(θ) * i_beta  - sin(θ) * i_alpha
```

**Code location:** `mcpwm_foc.c:4599–4601` (uses precomputed `phase_sin`, `phase_cos`)

**Result:** `(id, iq)` — currents in the rotor's reference frame. If the motor is spinning at constant speed with constant load, id and iq are DC values. The Park transform "derotates" the signals.

**What they mean physically:**
- **id** — current component aligned with the rotor's permanent magnet flux (d-axis). Zero in normal operation. Field weakening uses positive Id.
- **iq** — current component perpendicular to flux (q-axis). Directly produces torque. Proportional to motor torque: `T = K_t × iq`.

---

## The Angle θ

Both transforms require the rotor's electrical angle. This is the critical input — if θ is wrong, the transforms fail and control collapses.

θ comes from:
- **Encoder:** High accuracy, hardware position sensor
- **Hall sensors:** 6 discrete points per electrical revolution, interpolated
- **Sensorless observer:** Software estimate from back-EMF; accurate above `foc_sl_erpm`

The observer maintains `m_phase_now_observer` and the PLL maintains `m_pll_phase` for speed tracking. These are in `motor_all_state_t` (foc_math.h:138).

---

## Inverse Park Transform (Control → Stationary)

After the PI control computes the desired voltages (vd, vq), they must be rotated back to the stationary frame for SVM:

```
v_alpha = cos(θ) * vd - sin(θ) * vq
v_beta  = sin(θ) * vd + cos(θ) * vq
```

**Code location:** `mcpwm_foc.c:4701–4703`

**Result:** `(v_alpha, v_beta)` — voltage vector in stator frame, ready for [[space-vector-modulation|Space Vector Modulation]].

---

## Full Forward/Reverse Path Summary

```
[ia, ib, ic]  →  Clarke  →  [i_alpha, i_beta]  →  Park(θ)  →  [id, iq]
                                                                    ↓
                                                              PI control
                                                            target: id=0, iq=I_cmd
                                                                    ↓
[duty_A, duty_B, duty_C]  ←  SVM  ←  [v_alpha, v_beta]  ←  inv.Park(θ)  ←  [vd, vq]
```

---

## `phase_sin` and `phase_cos`

VESC precomputes the sin and cos of the current rotor angle each cycle and stores them in `motor_state_t`:

```c
// motor_state_t (foc_math.h:26)
float phase;      // Current rotor angle
float phase_sin;  // sin(phase) — precomputed for reuse
float phase_cos;  // cos(phase) — precomputed for reuse
```

This avoids computing trigonometry twice per cycle (once for forward Park, once for inverse Park). Both transforms use the same angle values.

---

## References

- [[bldc/motor/mcpwm_foc.c]] — Clarke at lines 3271–3279, Park at 4599–4601, inverse Park at 4701–4703
- [[bldc/motor/foc_math.h]] — `motor_state_t` lines 26–66 (id, iq, phase_sin, phase_cos)
- [[foc-overview|FOC Overview]] — where Clarke/Park fits in the full FOC loop
- [[current-pi-loop|Current PI Loop]] — PI control between forward and inverse Park
- [[space-vector-modulation|Space Vector Modulation]] — receives (v_alpha, v_beta) after inverse Park
