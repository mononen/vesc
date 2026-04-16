---
title: "Fault Detection"
aliases:
  - "Fault Detection"
tags:
  - safety
  - fault
  - crash
  - protection
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/main.c
---

# Fault Detection

Fault detection is the mechanism by which Refloat decides to stop the motor and transition from `RUNNING` to `READY`. It runs every main loop cycle (~1 kHz) while the board is active. Each fault type has its own timer and threshold.

The core `check_faults()` function in `main.c:354–490` implements all fault logic.

---

## Fault Types

### Pitch Fault — `STOP_PITCH`

```c
if abs(balance_pitch) > fault_pitch:
    pitch_timer += dt
    if pitch_timer > fault_delay_pitch / 1000.0:
        → STOP_PITCH
else:
    pitch_timer = 0   // Reset timer if angle recovers
```

**When this triggers:** Nose is too far up or down (board pitched beyond `fault_pitch` degrees). This catches genuine crashes where the rider has lost control and the board is nearly vertical.

**`fault_delay_pitch`:** Time in milliseconds that the angle must remain exceeded before stopping. A value of 100–200ms filters out momentary over-angles from bumps or landing pops. Zero means any single sample triggers immediately.

---

### Roll Fault — `STOP_ROLL`

```c
if abs(roll) > fault_roll:
    roll_timer += dt
    if roll_timer > fault_delay_roll / 1000.0:
        → STOP_ROLL
```

**When this triggers:** Board tipped sideways beyond `fault_roll` degrees. Catches tipping-over crashes. In darkride mode, the threshold is inverted (expecting > 90° roll).

---

### Full Switch Fault — `STOP_SWITCH_FULL`

```c
if footpad.state == FS_NONE:
    switch_timer += dt
    if switch_timer > fault_delay_switch_full:
        → STOP_SWITCH_FULL
else:
    switch_timer = 0
```

**When this triggers:** Both footpads released. The primary rider-off detection. The delay allows brief footpad interruptions (bumps causing momentary lift) without stopping.

**Speed-awareness:** At higher speeds, a shorter effective delay is used — the board stops more quickly when moving fast with no foot contact.

**`fault_moving_fault_disabled`:** When enabled, switch faults are suppressed above a speed threshold. Useful for riding styles where footpad contact may be momentarily interrupted during technical maneuvers.

---

### Half Switch Fault — `STOP_SWITCH_HALF`

```c
if footpad.state IN (FS_LEFT, FS_RIGHT):
    if abs_erpm < fault_adc_half_erpm:
        half_switch_timer += dt
        if half_switch_timer > fault_delay_switch_half:
            → STOP_SWITCH_HALF
```

**When this triggers:** Only one pad active, AND the board is at low speed. At low speed, single-pad contact typically means the rider is stepping off. At higher speeds, a single-pad state is tolerated (governed by `fault_moving_fault_disabled`).

This fault does NOT trigger at high speed — if you're moving fast with one foot on, the board keeps going.

---

### Quickstop — `STOP_QUICKSTOP`

```c
if enable_quickstop
   AND footpad.state == FS_NONE
   AND abs_erpm < 200           // Nearly stopped
   AND abs(pitch) > 14.0        // Board significantly tilted
   AND pitch * erpm_sign < 0:  // Tilted against direction of travel
    → STOP_QUICKSTOP
```

**When this triggers:** The board is nearly stationary, the rider has both feet off, and the board is leaning in the "stopping" direction (nose up if moving forward, nose down if moving backward). This recognizes an intentional dismount at low speed and stops immediately without waiting for `fault_delay_switch_full`.

This makes deliberate dismounting feel crisp — step off cleanly and the board stops instantly, rather than twitching forward for 500ms.

---

### Reverse Stop — `STOP_REVERSE_STOP`

Managed by [[reverse_stop.c]]. Triggers when the board has traveled a configurable distance in reverse without a deliberate reverse-stop mode engagement. Prevents unintended reverse runaway.

---

## Darkride Faults

When `state.darkride` is true (board upside-down), fault logic is modified:

- **Pitch fault:** Threshold is applied to the inverted pitch angle
- **Roll fault:** Triggered when roll drops *below* ~120° (returning toward rightside-up from inverted)
- **Footpad:** Same rules, but footpad is also inverted physically
- **Reverse stop:** More aggressive in darkride to prevent extended reverse from an inverted position

---

## Fault Timer Pattern

All faults use the same timer pattern: the timer accumulates while the fault condition is true, and resets to zero when the condition clears. The timer must exceed its threshold continuously — if the angle dips back below `fault_pitch` even briefly, the timer resets and must build up again.

This creates hysteresis: a brief recovery resets the fault timer, preventing stop on transient events.

---

## After a Fault

On stop:
1. `stop_condition` is set in the `State` struct (diagnostic)
2. Motor is released (freewheeled)
3. Data recorder stops
4. Haptic click plays
5. State transitions to `STATE_READY`

The stop condition is readable via telemetry — useful for understanding why the board stopped after a crash.

If `STOP_SWITCH_FULL` triggered (footpad fully released), the next engagement uses expanded `startup_pitch_tolerance` to support dirty-landing recovery.

---

## References

- [[main.c]] — `check_faults()` lines 354–490, full fault logic
- [[refloat-config|RefloatConfig]] — all `fault_*` parameters at `datatypes.h:208–312`
- [[footpad-sensor|Footpad Sensor]] — footpad state driving switch fault logic
- [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] — pitch and roll values checked against thresholds
- [[state-machine|State Machine]] — fault → `STOP_*` → READY transition
- [[tuning-engagement|Tuning Engagement and Startup]] — configuring fault thresholds and delays
