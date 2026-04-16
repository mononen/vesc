---
title: "Refloat–BLDC Interface"
aliases:
  - "Refloat–BLDC Interface"
tags:
  - architecture
  - api
  - interface
  - refloat
  - bldc
date: 2026-04-16
source_files:
  - refloat/vesc_pkg_lib/vesc_c_if.h
  - refloat/src/motor_control.c
  - bldc/motor/mc_interface.h
---

# Refloat–BLDC Interface

Refloat and bldc are separate codebases that communicate through a single abstraction layer: the `vesc_c_if` function pointer table. Every motor command Refloat sends, every sensor value it reads, goes through this interface.

---

## The `vesc_c_if` Table

Defined in `vesc_pkg_lib/vesc_c_if.h`, this is a struct of function pointers populated by bldc at runtime before the package starts. Refloat calls functions through it like:

```c
VESC_IF->mc_set_current(current);
VESC_IF->mc_get_rpm();
VESC_IF->imu_startup_done();
```

This indirection is what makes packages hardware-agnostic — the same Refloat binary runs on any VESC hardware variant, because the function pointers adapt to whatever hardware is underneath.

---

## Motor Control Commands

| Function | Effect |
|----------|--------|
| `VESC_IF->mc_set_current(float A)` | Command motor torque current (amps). This is the primary balance output. |
| `VESC_IF->mc_set_brake_current(float A)` | Apply braking current (always opposes motion). |
| `VESC_IF->mc_set_current_off_delay(float s)` | Set motor freewheel delay before cutting power. Used during traction control. |
| `VESC_IF->mc_release_motor()` | Freewheel — remove all current, let motor coast. |

**How `mc_set_current` becomes motor movement:**

```
VESC_IF->mc_set_current(I)
  → mc_interface_set_current(I)           [bldc/motor/mc_interface.c]
    → mcpwm_foc_set_current(I)            [bldc/motor/mcpwm_foc.c]
      → m_iq_set = I / phase_factor       [sets Q-axis current target]
        → next FOC ISR reads m_iq_set
          → PI control targets that Iq
            → PWM duty updated
```

The FOC loop runs at 20 kHz, so the current setpoint is actually executed within 50 µs of being written.

---

## Telemetry Reads

| Function | Returns |
|----------|---------|
| `VESC_IF->mc_get_rpm()` | Electrical RPM (signed) |
| `VESC_IF->mc_get_tot_current_filtered()` | Filtered motor current (A) |
| `VESC_IF->mc_get_duty_cycle_now()` | Current PWM duty (0.0–1.0) |
| `VESC_IF->mc_get_input_voltage_filtered()` | Battery voltage (V) |
| `VESC_IF->mc_temp_fet_filtered()` | MOSFET temperature (°C) |
| `VESC_IF->mc_temp_motor_filtered()` | Motor temperature (°C) |
| `VESC_IF->mc_get_input_current_filtered()` | Battery draw current (A) |

All of these are updated by the bldc FOC ISR and are safe to read from the main thread.

---

## IMU Callback Registration

The most important interface call:

```c
VESC_IF->set_imu_process_callback(imu_ref_callback);
```

This registers Refloat's `imu_ref_callback` to be called inside bldc's IMU interrupt, once per IMU sample. This is what gives Refloat its high-frequency control path — it piggybacks on bldc's existing IMU timing.

Without this, Refloat would have to poll the IMU from the main thread at ~1 kHz, which is insufficient for stable balance control.

---

## IMU Data Access

After registering the callback, Refloat runs its own [[mahony-ahrs-filter|Mahony AHRS Filter]] (`balance_filter.c`) using the raw gyro/accel data passed to the callback. It does NOT use bldc's IMU angle estimates (`VESC_IF->imu_get_pitch()`, etc.) for balancing — it computes its own more accurate estimate.

bldc's IMU API is still available:
```c
VESC_IF->imu_get_pitch()    // bldc's angle estimate (less precise for balance)
VESC_IF->imu_get_gyro(arr)  // Raw gyro [rad/s]
VESC_IF->imu_get_accel(arr) // Raw accel [m/s²]
```

Refloat uses these primarily for diagnostics and to check `imu_startup_done()` before transitioning out of STARTUP state.

---

## Configuration Access

```c
VESC_IF->get_cfg_float(CFG_PARAM_*)   // Read bldc motor config parameters
VESC_IF->set_cfg_float(CFG_PARAM_*, val) // Write motor config parameters
```

Refloat reads `mc_configuration` values (current limits, temperature limits) to enforce its own safety logic — for example, reading `l_current_max` to clamp balance current output.

---

## EEPROM Storage

Refloat's `RefloatConfig` is stored in VESC's EEPROM emulation via:
```c
VESC_IF->store_backup_data()      // Write to persistent storage
VESC_IF->read_backup_data()       // Read from persistent storage
```

This is how configuration survives power cycles without needing a separate storage chip.

---

## Communication / Telemetry Out

```c
VESC_IF->send_app_data(data, len)  // Send proprietary packet to VESC Tool
```

Used for Refloat's real-time telemetry stream — the `REALTIME_DATA` packets that VESC Tool displays as charts. This is how you see `setpoint`, `atr.setpoint`, `balance_pitch`, etc. updating live while riding.

---

## References

- [[refloat/vesc_pkg_lib/vesc_c_if.h]] — full function pointer table definition
- [[refloat/src/motor_control.c]] — `motor_control_apply()` lines 53–118, wraps `VESC_IF->mc_set_current`
- [[bldc/motor/mc_interface.h]] — function declarations that `vesc_c_if` pointers target
- [[system-overview|System Overview]] — where this interface fits in the two-codebase architecture
- [[thread-model|Thread Model and Timing]] — IMU callback registration and timing
- [[foc-overview|FOC Overview]] — what happens inside bldc after `mc_set_current` is called
