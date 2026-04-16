---
title: "Tuning Engagement and Startup"
aliases:
  - "Tuning Engagement and Startup"
tags:
  - tuning
  - startup
  - engagement
  - footpad
  - safety
  - practical
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/main.c
  - refloat/src/footpad_sensor.c
  - refloat/src/conf/datatypes.h
---

# Tuning Engagement and Startup

Engagement is the moment the board transitions from `READY` to `RUNNING` — the instant it starts actively balancing. Getting this right determines whether your board feels crisp and reliable to mount, or frustratingly picky, or conversely, dangerously easy to accidentally trigger.

See [[state-machine|State Machine]] for the full READY → RUNNING transition logic.

---

## The Engagement Check (`can_engage()`)

Before the board enters `RUNNING`, it verifies all of these simultaneously:

1. Board is in a valid startup angle (pitch and roll within tolerances)
2. Valid footpad contact (both pads, or single pad if configured)
3. Not charging
4. Not stuck in a disqualifying fault state

All conditions must pass simultaneously. The board will not engage if even one fails.

---

## Pitch and Roll Tolerance

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `startup_pitch_tolerance` | 10–35° | Maximum pitch deviation from level for valid startup |
| `startup_roll_tolerance` | 10–45° | Maximum roll deviation from level for valid startup |

### Tuning Guidance

**`startup_pitch_tolerance`** controls how nose-up or nose-down the board can be when you try to engage. A tight tolerance (10–15°) means you must start on very level ground or with the board very carefully balanced. A loose tolerance (30–35°) allows engaging on a ramp or from an off-angle position.

**Common scenario — board refuses to engage on a slope:**
Your driveway or parking spot has enough of a grade that the board's pitch exceeds `startup_pitch_tolerance`. Increase the tolerance to 30–35°.

**Safety note:** Very large pitch tolerance (> 40°) allows engaging on nearly vertical surfaces. The board will immediately try to balance but the setpoint-centering ramp will handle the large initial error. This is usually safe but can feel abrupt if the initial error is large.

**`startup_roll_tolerance`** is almost always set loosely because roll doesn't matter for balance — you can engage the board while it's tilted sideways (leaning against a wall, for instance). Most riders set this to 45° or ignore it entirely.

**After a crash (dirty landing tolerance):**
When the board stops due to `STOP_SWITCH_FULL` (footpad released in the air), it expands the pitch tolerance temporarily by adding a margin. This allows you to catch the board while it's moving and step back on without needing to set it perfectly level first. See `startup_dirtylandings_enabled`.

---

## Footpad Configuration

### Parameters

| Parameter                     | Typical Range | Effect                                          |
| ----------------------------- | ------------- | ----------------------------------------------- |
| `fault_adc1`                  | 0.05–0.5 V    | ADC threshold for front footpad contact         |
| `fault_adc2`                  | 0.05–0.5 V    | ADC threshold for rear footpad contact          |
| `fault_is_dual_switch`        | true/false    | Require both pads to engage (true = safer)      |
| `startup_simplestart_enabled` | true/false    | Allow single-pad start after 2 seconds in READY |

### Tuning Guidance

**`fault_adc1` / `fault_adc2` thresholds:** These determine how much pressure constitutes "foot on pad." Too high and the pad triggers even with light contact (risk of false engagement). Too low and you need to press hard before the board will engage or stay on.

Start at 0.1 V and raise if you're getting false triggers. If the board disengages while riding with normal foot pressure, lower the threshold. Check raw ADC readings via telemetry (`adc1`, `adc2`) to see your actual values while riding.

**`fault_is_dual_switch`:** When true, both footpads must be active for the board to engage. This prevents one-footed accidental triggers. Required for high-speed riding — single-pad disengagement at speed is dangerous.

When false (single-switch mode), the board can engage and ride with only one pad active. Some riders use this for learning, tricks, or one-footed maneuvers.

**`startup_simplestart_enabled`:** When true, after sitting in READY for 2 seconds with only one pad active, the board will engage on the single pad. This is a convenience feature for mounts where you can't get both pads down simultaneously.

---

## Startup Speed and Centering

When the board engages, it doesn't just switch on at full PID immediately — it runs a centering sequence that ramps the setpoint from the current board angle toward level.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `startup_speed` | 30–60 °/s | Rate at which the setpoint moves to level on startup |

### Tuning Guidance

**High `startup_speed` (50–60 °/s):** The board snaps to level quickly after engagement. Feels crisp and immediate. Can be surprising if you're not ready — the board pushes firmly against your weight.

**Low `startup_speed` (20–30 °/s):** The board eases into balance gently. Better for learning or for people who mount slowly. Can feel sluggish to experienced riders.

**Softstart interaction:** Even with a fast `startup_speed`, the motor current ramps up gradually via the softstart mechanism (100 A/s). This prevents the motor from jerking at engagement. You don't tune this directly — it's hardcoded in `main.c`.

---

## Haptic Click on Engagement

The startup click is both feedback (confirms engagement) and functional (a small current pulse that wiggles the motor slightly, letting the rider feel the board is live).

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `startup_click_current` | 1–10 A | Current magnitude for the engagement click |

**Tuning:** A click around 3–5 A is subtle but noticeable — one small bump underfoot. Higher values (7–10 A) produce a more definitive clunk. Lower values (1–2 A) may be too subtle to feel through shoes.

Set this to whatever makes engagement confirmation feel reliable to you. There's no safety implication — the click is momentary.

---

## Push-Start (Dirty Landings)

Dirty landings / push-start allows the board to re-engage while it's rolling, without requiring a stationary mount. This is critical for catching the board after a bail where it's still rolling away from you.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `startup_pushstart_enabled` | true/false | Enable push-start / dirty landing recovery |
| `startup_dirtylandings_enabled` | true/false | Expand pitch tolerance for dirty landings specifically |

### How Push-Start Works

When in `READY` state with the board rolling (`abs_erpm > 1000`) and footpad contact is valid, the board checks whether the pitch is within a (potentially expanded) tolerance. If so, it engages even though the board is moving.

The ERPM threshold means the board can't be accidentally engaged by a light nudge — it requires meaningful rolling motion.

**Tuning:** Most riders enable both. Disabling push-start means you must stop the board completely to remount after a bail, which can be difficult and dangerous if the board rolls away. Enable `startup_dirtylandings_enabled` to expand the pitch tolerance specifically during rolling recovery — this allows the board to engage even if the pitch is slightly off because you caught it in motion.

---

## Fault Delays and Hysteresis

These parameters control how long a fault condition must persist before the board stops. They prevent instantaneous shutoffs from transient sensor events (a single ADC glitch, a momentary footpad slip).

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `fault_delay_pitch` | 0–500 ms | How long pitch must exceed `fault_pitch` before stopping |
| `fault_delay_roll` | 0–500 ms | How long roll must exceed `fault_roll` before stopping |
| `fault_delay_switch_half` | 0–500 ms | How long single-pad contact is tolerated at low speed |
| `fault_delay_switch_full` | 0–500 ms | How long no-pad contact is tolerated |

### Tuning Guidance

**`fault_delay_pitch`:** Setting this to 0 means any single control loop iteration over the pitch limit causes a stop — very harsh. At 100–200ms, you have a brief grace period where an instantaneous over-pitch (landing from a small jump) won't immediately disengage the board. Most riders use 100–200ms.

**`fault_delay_switch_full`:** Time with no footpad contact before the board stops. At 0ms, lifting a foot for any reason causes immediate cutoff. At 500ms, you can briefly lift both feet (trick, foot adjustment) without stopping. Higher values are more trick-friendly but reduce safety.

**`fault_delay_switch_half`:** Time with only one pad active before stopping (at low speed). At low speed (below `fault_adc_half_erpm`), the board requires both pads. This delay sets how long a single-pad state is tolerated. Higher values allow longer one-footed coasting at low speed.

**`fault_moving_fault_disabled`:** When enabled, switch faults are suppressed while the board is rolling normally above a speed threshold. This is a "moving fault disable" — the theory being that if you're riding normally at speed, brief footpad interruptions are unlikely to be real dismounts. Useful for technical riding where footpad contact may be intermittent.

---

## Fault Angle Thresholds

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `fault_pitch` | 25–50° | Maximum nose-up or nose-down angle before stopping |
| `fault_roll` | 40–70° | Maximum roll before stopping |

### Tuning Guidance

**`fault_pitch`:** This is your crash detection threshold. If the board pitches beyond this angle (nose too far up or down), it assumes the rider is no longer on it and stops. Too tight (20°) and the board stops during aggressive maneuvers. Too loose (55°+) and the board may stay on after a genuine crash.

**Standard range:** 35–45°. This allows aggressive riding postures but catches most genuine falls.

**`fault_roll`:** The board can roll (tip sideways) quite far before it's clearly fallen over. Darkride mode (upside-down riding) uses a roll threshold of ~150° — if `fault_darkride_enabled` is true, the firmware doesn't fault until roll exceeds that. For normal riding, 40–55° is appropriate.

---

## Reverse Stop

If a rider pushes the board backward (negative ERPM) beyond a configurable distance, `STOP_REVERSE_STOP` triggers. This prevents riding in reverse indefinitely without explicit reverse-stop mode engagement.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `fault_reversestop_enabled` | true/false | Enable reverse stop feature |

When enabled, riding in reverse for too long or too far will trigger a graceful stop. See [[reverse_stop.c]] for the specific thresholds.

---

## Quickstop

Quickstop is a fast emergency stop at low speed. If the board is barely moving, both footpads are off, the pitch is significantly tilted, and the board is pitching in the correct direction for a stop, it cuts power immediately rather than waiting for the full fault delays.

### Parameters

| Parameter | Typical Range | Effect |
|-----------|--------------|--------|
| `enable_quickstop` | true/false | Enable quickstop feature |

**When to enable:** Most riders enable this. It makes deliberate dismounting at low speed crisp — step off cleanly and the board stops immediately. Without it, the full `fault_delay_switch_full` plays out, during which the board may wander.

---

## References

- [[main.c]] — `can_engage()` lines 325–351; `engage()` lines 261–290; `check_faults()` lines 354–490
- [[footpad_sensor.c]] — ADC reading, state classification (`FS_NONE/LEFT/RIGHT/BOTH`)
- [[state.h]] — `StopCondition` enum (PITCH, ROLL, SWITCH_HALF, SWITCH_FULL, REVERSE_STOP, QUICKSTOP)
- [[refloat-config|RefloatConfig]] — all `startup_*`, `fault_*` fields at `datatypes.h:208–312`
- [[state-machine|State Machine]] — full READY ↔ RUNNING transition logic
- [[fault-detection|Fault Detection]] — detailed fault checking logic
- [[footpad-sensor|Footpad Sensor]] — sensor hardware and state classification
