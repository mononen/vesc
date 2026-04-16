---
title: "State Machine"
aliases:
  - "State Machine"
tags:
  - safety
  - state-machine
  - architecture
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/state.h
  - refloat/src/state.c
  - refloat/src/main.c
---

# State Machine

Refloat's state machine controls the board's lifecycle from power-on through riding and crashes. It is the authority on whether the board is actively balancing, waiting for a rider, or disabled.

---

## `RunState` — The Primary State

```c
// state.h:23
typedef enum {
    STATE_DISABLED,  // Package disabled in config
    STATE_STARTUP,   // IMU initializing
    STATE_READY,     // Waiting for rider
    STATE_RUNNING    // Actively balancing
} RunState;
```

### DISABLED
Set when `float_conf.disabled` is true. No balancing, no fault checking. The board is inert.

### STARTUP
Initial state on boot. Waits for `VESC_IF->imu_startup_done()` to return true — the IMU needs time to initialize and the Mahony filter needs to converge before balance angles are reliable. Checks low battery level and beeps accordingly.

### READY
IMU is ready, board is waiting for a rider. The board continuously checks `can_engage()` and polls for push-start conditions. All fault timers are reset. If the board is upside-down (roll > 150°) and `fault_darkride_enabled`, darkride mode arms.

### RUNNING
Actively balancing. The IMU callback is running PID control. Every main loop cycle, `check_faults()` is called. If any fault triggers, transitions back to READY.

---

## `Mode` — Operating Mode

```c
typedef enum {
    MODE_NORMAL,    // Standard riding
    MODE_HANDTEST,  // Motor limited to 7A — for bench testing
    MODE_FLYWHEEL   // Self-balancing without footpad requirement
} Mode;
```

**Flywheel mode** is activated via Konami code sequence on the footpad. In this mode, the footpad fault checks are suppressed — the board balances indefinitely without a rider. Used for tricks, display, or testing.

---

## `SetpointAdjustmentType (SAT)` — Safety Tiltback State

```c
typedef enum {
    SAT_NONE,           // Normal riding, no tiltback
    SAT_CENTERING,      // Startup: setpoint centering toward 0
    SAT_REVERSESTOP,    // Reverse stop active
    SAT_PB_SPEED,       // Speed tiltback
    SAT_PB_DUTY,        // Duty cycle tiltback
    SAT_PB_ERROR,       // Firmware error tiltback
    SAT_PB_HIGH_VOLTAGE,// High voltage tiltback
    SAT_PB_LOW_VOLTAGE, // Low voltage tiltback
    SAT_PB_TEMPERATURE  // Temperature tiltback
} SetpointAdjustmentType;
```

SAT is set by `calculate_setpoint_target()` each main loop cycle. It determines which tiltback angle and speed the base setpoint moves toward. See [[pushback-tiltback|Pushback and Tiltback System]] for the full SAT priority hierarchy.

---

## `StopCondition` — Why the Board Stopped

```c
typedef enum {
    STOP_NONE,
    STOP_PITCH,        // Nose too far up or down
    STOP_ROLL,         // Tipped sideways too far
    STOP_SWITCH_FULL,  // Both footpads released
    STOP_SWITCH_HALF,  // Single pad at low speed
    STOP_REVERSE_STOP, // Reverse distance limit triggered
    STOP_QUICKSTOP     // Low-speed quickstop
} StopCondition;
```

Set when `check_faults()` triggers a stop. Available in telemetry for post-ride analysis of why the board stopped.

---

## State Transitions

### STARTUP → READY
```
Trigger: VESC_IF->imu_startup_done() returns true
Action:  Reset all runtime variables, check battery voltage, beep low-battery warning
```

### READY → RUNNING (`can_engage()`)
```
Requires all of:
  - abs(balance_pitch) < startup_pitch_tolerance
  - abs(roll) < startup_roll_tolerance
  - footpad state is valid (BOTH, or single with simplestart/no-dual-switch)
  - NOT charging
  - NOT in a blocking fault condition

On engage:
  - Reset PID, tilts, filters
  - Play haptic click
  - Trigger data recorder
  - Set state = STATE_RUNNING, SAT = SAT_CENTERING
```

### RUNNING → READY (`check_faults()`)
```
Triggers:
  - pitch > fault_pitch for fault_delay_pitch ms  → STOP_PITCH
  - roll > fault_roll for fault_delay_roll ms     → STOP_ROLL
  - FS_NONE for fault_delay_switch_full ms        → STOP_SWITCH_FULL
  - Single pad at low ERPM for switch_half ms     → STOP_SWITCH_HALF
  - Reverse stop limit                            → STOP_REVERSE_STOP
  - Low-speed quickstop conditions                → STOP_QUICKSTOP

On stop:
  - Set stop_condition
  - Play click sound
  - Stop data recorder
  - Release motor
  - state = STATE_READY
```

### READY → Darkride
```
Trigger: roll > 150° AND fault_darkride_enabled
Action:  Set state.darkride = true
         Future engagement: sign-inverted balance_pitch and motor current
```

---

## The `State` Struct

```c
// state.h:60–68
State {
    RunState state;               // Primary state
    Mode mode;                    // Operating mode
    SetpointAdjustmentType sat;   // Current tiltback state
    StopCondition stop_condition; // Why we last stopped
    bool charging;                // Charge port connected
    bool wheelslip;               // Traction control active
    bool darkride;                // Board upside-down mode
}
```

---

## References

- [[state.h]] — enum definitions lines 23–68
- [[main.c]] — `can_engage()` lines 325–351, `engage()` lines 261–290, `check_faults()` lines 354–490, state machine transitions lines 863–1082
- [[fault-detection|Fault Detection]] — `check_faults()` logic in detail
- [[footpad-sensor|Footpad Sensor]] — footpad state required for READY → RUNNING
- [[pushback-tiltback|Pushback and Tiltback System]] — SAT hierarchy and setpoint effects
- [[traction-control|Traction Control and Wheelslip]] — `state.wheelslip` flag
