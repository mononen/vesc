---
title: "Thread Model and Timing"
aliases:
  - "Thread Model and Timing"
tags:
  - architecture
  - threading
  - timing
  - chibiOS
  - refloat
  - bldc
date: 2026-04-16
source_files:
  - refloat/src/main.c
  - refloat/src/frequency_tracker.c
  - bldc/motor/mcpwm_foc.c
---

# Thread Model and Timing

The onewheel control system runs across multiple threads and interrupt service routines at very different frequencies. Understanding the timing model is important for understanding why parameters behave the way they do, and what "loop frequency" actually means.

---

## The Thread Stack

From highest to lowest priority:

| Context | Frequency | What Runs |
|---------|-----------|-----------|
| FOC ISR (bldc) | ~20 kHz | Clarke/Park transforms, Id/Iq PI control, SVM, PWM update |
| IMU callback (Refloat) | ~20–30 kHz | Mahony filter, PID, motor current command |
| Speed PID (bldc) | ~1 kHz | Speed/position PID loop |
| Main thread (Refloat) | ~1000 Hz | Tilt calculations, setpoint, fault checking, sensors |
| Peripheral threads | ~100 Hz | LED, BMS, data recorder, alerts |

---

## Refloat's Two Contexts

### IMU Callback — The Critical Path

`imu_ref_callback()` is registered into bldc's IMU ISR via:
```c
VESC_IF->set_imu_process_callback(imu_ref_callback);
```

It runs at the IMU hardware sample rate. This is where balance happens:

```
IMU hardware interrupt fires
  → bldc reads gyro/accel raw values
  → bldc updates its own Mahony filter
  → bldc calls Refloat's imu_ref_callback()
    → Refloat updates its own Mahony filter (balance_filter.c)
    → Extracts balance_pitch, pitch_rate
    → Runs PID control
    → Adds booster current
    → Calls VESC_IF->mc_set_current()
  → bldc ISR continues into FOC control_current()
  → PWM timers updated
```

The total latency from IMU data to PWM update is sub-millisecond. This tight loop is why the board can maintain balance — any longer latency and the inverted pendulum would fall before the correction arrived.

### Main Thread — The Setpoint Computer

`refloat_thd()` is a [[thread-model|ChibiOS]] thread at `NORMALPRIO`. It runs a `while(1)` loop with a sleep at the end to target ~1000 Hz.

```c
while (!VESC_IF->should_terminate()) {
    // ... all tilt calculations, fault checks, sensor reads ...
    VESC_IF->sleep_us(loop_time_us);
}
```

The actual achieved frequency is tracked by `FrequencyTracker` and reported in telemetry. Actual frequency may vary from the configured `hertz` parameter due to scheduling jitter.

---

## Why PID Runs at IMU Rate, Not Main Loop Rate

The IMU callback runs the PID because:

1. **Latency:** Motor commands must happen within microseconds of the angle estimate. A 1ms delay (one main loop cycle) at a 50° nosedive would mean ~3° of additional fall before correction.

2. **Sample rate:** The PID derivative term (`rate_p = -kp2 * pitch_rate`) needs the fresh gyro reading from the same IMU sample. Waiting for the main loop would mean derivative data that's 1ms stale.

3. **Consistency:** Running at IMU rate means the PID timing is hardware-driven, not OS-driven. The main loop has scheduling jitter; the IMU ISR does not.

The tradeoff: setpoints computed by the main thread are consumed by the IMU callback on its next cycle. There's a potential 1ms setpoint latency, but setpoints change slowly (they're rate-limited by tilt algorithm ramp speeds), so this is acceptable.

---

## bldc's Thread Structure

bldc uses [[thread-model|ChibiOS]] for all threading:

**FOC ISR (interrupt context):**
- `mcpwm_foc_adc_int_handler()` — runs at PWM switching frequency (~20 kHz)
- Reads ADC current samples, runs `control_current()`, updates PWM timers
- Highest priority — cannot be preempted

**Speed PID thread (`pid_thread`):**
- Runs at ~1 kHz
- Updates `iq_set` (torque current target) based on speed error
- Not used when Refloat directly commands current

**HFI thread (`hfi_thread`):**
- High-Frequency Injection for sensorless startup
- Only active below `foc_sl_erpm` threshold (typically < 500 ERPM)

**Flash integrity thread:**
- Runs every 6ms, checks flash CRC
- Triggers system reset on corruption

---

## The `hertz` Parameter

`RefloatConfig.hertz` sets the target frequency for Refloat's main loop. Default is typically 1000 Hz. The actual achieved frequency is logged as `main_frequency` in telemetry.

If `main_frequency` is consistently below `hertz`, the system is overloaded. Causes:
- Too many active subsystems (LEDs, data recording, BMS polling)
- ChibiOS scheduling contention
- Slow hardware (lower-end VESC variants)

The frequency tracker (`frequency_tracker.c`) also monitors the IMU callback rate (`imu_frequency`). If this is significantly lower than expected, there may be an IMU configuration or hardware issue.

---

## `dt` in Calculations

Many algorithms use `dt` (delta time, seconds per loop). For the main loop:

```c
dt = 1.0 / main_frequency  // typically 0.001 s at 1000 Hz
```

For the IMU callback:

```c
dt = imu_dt  // time since last IMU sample, typically ~0.00004 s at 25 kHz
```

The IMU `dt` is used in the PID integrator and Mahony filter. The main loop `dt` is used in tilt algorithm ramp calculations. If the loop rate changes (e.g., at startup before it stabilizes), `dt`-based calculations adapt automatically.

---

## References

- [[refloat/src/main.c]] — `imu_ref_callback()` line 765, `refloat_thd()` line 788
- [[refloat/src/frequency_tracker.c]] — loop frequency monitoring
- [[bldc/motor/mcpwm_foc.c]] — FOC ISR line 2848, thread declarations lines 65–76
- [[system-overview|System Overview]] — architectural context for why these threads exist
- [[pid-controller|PID Controller]] — runs inside the IMU callback at high frequency
- [[mahony-ahrs-filter|Mahony AHRS Filter]] — also runs inside the IMU callback
