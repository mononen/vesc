---
title: "IMU: Pitch, Roll, Yaw"
aliases:
  - "IMU: Pitch, Roll, Yaw"
tags:
  - sensor
  - imu
  - pitch
  - roll
  - yaw
  - refloat
date: 2026-04-16
source_files:
  - refloat/src/imu.c
  - refloat/src/imu.h
---

# IMU: Pitch, Roll, Yaw

Refloat extracts three orientation angles and one angular rate from the [[mahony-ahrs-filter|Mahony AHRS Filter]] quaternion output. These angles define the board's spatial orientation and feed directly into the balance and ride-feel algorithms.

---

## Angle Definitions

For a onewheel, the axes are defined relative to the board and rider:

**Pitch** — Nose-up / nose-down rotation
- Positive pitch: nose up (leaning back)
- Negative pitch: nose down (leaning forward)
- This is the primary balance axis — the PID controls this angle

**Roll** — Side-to-side tilt
- Positive: right side down (left-leaning from rider's perspective)
- Used for fault detection (`fault_roll`) and darkride detection (> 150°)
- [[turn-tilt|Turn Tilt]] uses roll indirectly via yaw rate

**Yaw** — Rotation around the vertical axis (turning left/right)
- Absolute yaw relative to the initial heading
- Rate of yaw change used by [[turn-tilt|Turn Tilt]]

---

## `balance_pitch` vs `pitch`

The [[imu-pitch-roll-yaw|IMU: Pitch, Roll, Yaw]] struct contains two pitch-related values:

```c
IMU {
    float pitch;           // Raw pitch from Mahony quaternion
    float balance_pitch;   // Pitch corrected for balance use
    float roll;
    float yaw;
    float pitch_rate;
}
```

**`pitch`** — direct quaternion-to-Euler conversion. This is the true board angle.

**`balance_pitch`** — pitch adjusted for balance. The adjustment accounts for the IMU's physical mounting position on the board. If the IMU is not perfectly aligned with the board's balance axis, a correction offset is applied here. In darkride mode (board upside-down), `balance_pitch` has its sign inverted so the PID continues working correctly with inverted motor commands.

The [[pid-controller|PID Controller]] uses `balance_pitch`, not `pitch`.

---

## Pitch Rate

```c
float pitch_rate;   // degrees/second
```

This is the board's angular velocity around the pitch axis — how fast the nose is moving up or down. Computed directly from the gyroscope's Y-axis reading (after converting rad/s to deg/s and applying roll correction):

```c
// From imu.c:51
pitch_rate = -(gyro[1] * cos(roll_rad) - gyro[2] * sin(roll_rad)) * RAD2DEG
```

The roll correction ensures pitch rate remains accurate even when the board is rolled sideways (e.g., in a carve). The negative sign converts from the sensor's coordinate frame to the board's convention (nose-up is positive pitch, so nose-moving-up is positive pitch rate).

`pitch_rate` is used by the [[pid-controller|PID Controller]]'s `rate_P` term (`kp2 * -pitch_rate`) — it acts as a derivative term that damps pitch velocity, making the board feel stable rather than twitchy.

---

## Flywheel Mode Offsets

When flywheel mode is active (Konami code sequence on footpad), the IMU applies angle offsets:

```c
float flywheel_pitch_offset;   // Applied to pitch in flywheel mode
float flywheel_roll_offset;    // Applied to roll in flywheel mode
```

These allow the board to balance around a different center angle without retuning the PID. Flywheel mode holds the board upright without a rider — the offsets correct for the changed weight distribution.

---

## Darkride Mode Inversion

When `state.darkride` is true (board is upside-down, roll > 150°):

- `balance_pitch` sign is inverted
- Motor commands issued by the PID are also inverted (in `motor_control_apply()`)

This allows the same PID and setpoint logic to work for both normal and upside-down riding without any algorithm changes — only the sign conventions flip.

---

## References

- [[imu.c]] — `imu_update()` lines 35–66; pitch, roll, yaw extraction; `pitch_rate` calculation line 51
- [[imu.h]] — `IMU` struct definition: `pitch`, `balance_pitch`, `roll`, `yaw`, `pitch_rate`
- [[mahony-ahrs-filter|Mahony AHRS Filter]] — produces the quaternion that this module converts to angles
- [[pid-controller|PID Controller]] — uses `balance_pitch` as the process variable, `pitch_rate` as derivative input
- [[turn-tilt|Turn Tilt]] — uses `yaw` and `yaw_rate` for corner compensation
- [[state-machine|State Machine]] — uses `roll` for fault detection and darkride transition detection
