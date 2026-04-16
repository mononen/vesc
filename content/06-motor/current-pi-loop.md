---
title: "Current PI Loop"
aliases:
  - "Current PI Loop"
tags:
  - motor
  - foc
  - pid
  - current-control
  - bldc
date: 2026-04-16
source_files:
  - bldc/motor/mcpwm_foc.c
---

# Current PI Loop (Id/Iq Control)

After the [[clarke-park-transforms|Clarke and Park Transforms]] convert phase currents into `(id, iq)`, two PI controllers regulate these quantities to their targets. This is the inner-most control loop, running at 20 kHz inside the FOC ISR.

---

## The Two Controllers

**Id controller:** Drives `id` toward `id_target` (normally 0)
- Eliminates d-axis current that would waste energy without producing torque
- Non-zero `id_target` is used for field weakening at high speeds

**Iq controller:** Drives `iq` toward `iq_target` (the motor current commanded by Refloat)
- This is the torque-producing controller
- `iq_target` = `m_iq_set`, which is set when Refloat calls `VESC_IF->mc_set_current()`

---

## PI Control Law

```c
// mcpwm_foc.c:4599–4703

// D-axis:
Ierr_d = id_target - id
vd_int += Ierr_d * ki_d * dt
vd = vd_int + Ierr_d * kp_d

// Q-axis:
Ierr_q = iq_target - iq
vq_int += Ierr_q * ki_q * dt
vq = vq_int + Ierr_q * kp_q
```

**Note: no derivative term.** Current controllers are pure PI, not PID. Adding derivative to current control amplifies sensor noise and destabilizes the fast loop.

---

## Gain Calculation

The PI gains are not tuned manually — they're derived from motor parameters for a target bandwidth:

```c
// From VESC motor detection or manual entry:
L = foc_motor_l   // Motor inductance (H)
R = foc_motor_r   // Motor resistance (Ω)

// Current loop bandwidth = cross-over frequency
kp = bandwidth * L       // Bandwidth ~ 1/(2*pi*foc_f_zv/10)
ki = R / L               // Pole-zero cancellation
```

This ensures the current loop is critically damped for the specific motor's electrical characteristics. Incorrect `foc_motor_l` or `foc_motor_r` values produce either slow, sluggish current tracking or unstable oscillation.

---

## Decoupling Feedforward

PMSM motors have cross-coupling between d and q axes — the q-axis current creates a voltage in the d-axis (and vice versa) due to the rotating flux. Without compensation, the PI controllers must fight this coupling, which limits bandwidth.

VESC applies decoupling feedforward terms:

```c
// dec_vd compensates for q-axis induced voltage in d-axis
dec_vd = -ωe * L * iq       // Back-EMF cross-coupling

// dec_vq compensates for d-axis induced voltage in q-axis + back-EMF
dec_vq = ωe * L * id + ωe * flux_linkage    // Back-EMF

vd_total = vd + dec_vd
vq_total = vq + dec_vq
```

`ωe` is the electrical angular velocity (rad/s = ERPM * π / 30). At high speed, the decoupling terms dominate — most of the applied voltage is compensating back-EMF rather than driving current change.

---

## Anti-Windup and Voltage Saturation

The available voltage is limited by the battery voltage and modulation depth. If the PI controller demands more voltage than is available, the integral winds up — causing lag and overshoot when the saturation clears.

VESC handles this with a priority scheme:
1. D-axis gets priority — `vd_total` is clamped first to the available circle
2. Q-axis gets remaining headroom — `vq_total = sqrt(max_v² - vd²)` at most

This ensures field control (flux) is maintained even when torque demand saturates. For a balancing application, field weakening is rarely needed (speeds are moderate), so this rarely matters.

**Field Weakening:** Above a certain duty cycle (`foc_fw_duty_start`), `id_target` becomes negative (injecting negative d-axis current). This weakens the rotor's effective flux, allowing higher electrical speeds at the cost of efficiency. Effectively extends the motor's top speed beyond its natural BEMF-limited maximum.

---

## Key Config Parameters

From [[bldc-mc-configuration]] (`mc_configuration`):

| Parameter | Effect |
|-----------|--------|
| `foc_current_kp` | Proportional gain (derived from motor L) |
| `foc_current_ki` | Integral gain (derived from R/L ratio) |
| `foc_motor_l` | Motor inductance — affects kp calculation |
| `foc_motor_r` | Motor resistance — affects ki calculation |
| `foc_motor_flux_linkage` | Back-EMF constant — affects decoupling feedforward |
| `foc_fw_current_max` | Maximum field-weakening current |
| `foc_fw_duty_start` | Duty cycle threshold to begin field weakening |

---

## References

- [[bldc/motor/mcpwm_foc.c]] — `control_current()` lines 4550–4703; full PI law and decoupling
- [[foc-overview|FOC Overview]] — where the current loop fits in the full FOC stack
- [[clarke-park-transforms|Clarke and Park Transforms]] — produces `(id, iq)` consumed by these PI loops
- [[space-vector-modulation|Space Vector Modulation]] — receives `(vd, vq)` outputs
- [[bldc-mc-configuration]] — `foc_current_kp`, `foc_current_ki`, motor parameters
