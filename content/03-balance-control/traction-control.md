---
title: "Traction Control and Wheelslip"
aliases:
  - "Traction Control and Wheelslip"
  - "Traction Control"
tags:
  - safety
  - traction
  - wheelslip
  - control
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/main.c
---

# Traction Control and Wheelslip

Wheelslip occurs when the motor produces more torque than the tire can transmit to the ground — the wheel spins instead of propelling the board. When this happens, the normal control loop breaks down: the motor reports high ERPM but the board isn't actually accelerating. If uncorrected, the PID would demand even more current, worsening the slip.

Refloat detects wheelslip and responds by temporarily freewheeling the motor.

---

## Detection

Wheelslip is detected when all of these are true simultaneously:

```c
// main.c:512–534
acceleration > 10000 ERPM/s      // Wheel accelerating very fast
sign(acceleration) == sign(erpm) // Acceleration in the direction of travel (not braking)
duty_cycle > 0.3                 // Significant motor demand (not coasting)
abs_erpm > 2000                  // At meaningful speed
```

The key signal is `motor.acceleration` — the 40-sample SMA of ERPM change rate. On normal pavement, the tire limits how fast the wheel can spin up. During wheelslip, the wheel spins up much faster than traction allows, producing abnormally high ERPM acceleration.

The `acceleration > 10000 ERPM/s` threshold is empirically chosen. Normal hard acceleration is typically under 5000–7000 ERPM/s; wheelslip produces values well above 10000.

---

## Response

When wheelslip is detected:

```c
state.wheelslip = true;
VESC_IF->mc_set_current_off_delay(0.05);  // Allow 50ms coast-down
motor_control.requested_current = 0;       // Freewheel
```

The `mc_set_current_off_delay` tells the FOC layer to hold zero current for 50ms even if new current commands arrive — this ensures the wheel fully decelerates and regains traction before control resumes.

All tilt setpoints are wound down toward zero during wheelslip:
```c
torque_tilt.setpoint *= 0.995;   // 0.5% per cycle
atr.setpoint *= 0.995;
brake_tilt.setpoint *= 0.995;
turn_tilt.setpoint *= 0.995;
```

The base setpoint is held at its last value (not updated during wheelslip). The PID continues computing but its output is zeroed.

---

## Recovery

Wheelslip clears when:
```c
acceleration < 7000 ERPM/s       // Acceleration has normalized
AND duty_cycle < 0.85            // Not still at extreme demand
```

The hysteresis (10000 to detect, 7000 to clear) prevents rapid oscillation between wheelslip and normal states.

After clearing, `state.wheelslip = false` and normal tilt updates resume. The wound-down tilt setpoints ramp back up naturally over the next few cycles via their normal ramp speeds.

---

## Darkride (Upside-Down) Special Case

In darkride mode, when wheelslip is detected:
```c
traction_control = true;
motor_control.requested_current = NAN;   // Let motor freewheel without stopping balance
```

The distinction from normal wheelslip: in darkride, the board is upside-down and the motor current direction is already inverted. Using the same freewheel logic could cause the board to fall — instead, a separate flag handles the traction recovery without cutting balance entirely.

---

## Effect on Ride Feel

Effective traction control is nearly transparent on typical pavement. The motor cuts for 50ms, the board continues on momentum, and resumes control once traction is restored. At high speed, this may manifest as a brief surge of wheel speed followed by smooth continuation.

On very slippery surfaces (wet, polished stone, ice), wheelslip may trigger repeatedly. In these conditions, reducing `l_current_max` in [[bldc-mc-configuration]] reduces the peak torque and thus the slip tendency.

---

## References

- [[main.c]] — wheelslip detection lines 512–534, `traction_control` flag and freewheel handling
- [[motor-data|Motor Data]] — `motor.acceleration` (SMA-40 of ERPM), `motor.duty_cycle`
- [[state-machine|State Machine]] — `state.wheelslip` flag in the `State` struct
- [[setpoint-composition|Setpoint Composition]] — tilt setpoint winddown during wheelslip
- [[bldc-mc-configuration]] — `l_current_max` to reduce slip tendency
