# All Continuous Rotation Servos Configuration Guide

## Overview

If **all four of your servos are continuous rotation servos**, you need to use the alternate firmware and Python driver designed for this configuration.

## Files You Need

### Arduino Firmware
**File**: `arduino_servo_controller_all_continuous.ino`

This firmware treats ALL servos as continuous rotation:
- S1 (Pin 10): Door Lock - Continuous Rotation
- S2 (Pin 9): Pan/X-axis - Continuous Rotation  
- S3 (Pin 11): Tilt/Y-axis - Continuous Rotation
- S4 (Pin 6): Window Lock - Continuous Rotation

### Python Driver
**File**: `turret_controller_continuous.py`

This driver sends timed movement commands instead of position commands.

## How Continuous Rotation Servos Work

Unlike positional servos that move to a specific angle (0-180°), continuous rotation servos:
- **90°** = STOP
- **180°** = Full speed clockwise
- **0°** = Full speed counter-clockwise

You control them by:
1. Starting rotation in a direction
2. Timing how long they run
3. Stopping them

## Upload the Alternate Firmware

1. Open Arduino IDE
2. Open `arduino_servo_controller_all_continuous.ino`
3. Select your Arduino board and port
4. Upload

**Startup message will show:**
```
SERVO_READY
S1:IDLE
S2:IDLE
S3:IDLE
S4:IDLE
SHOOTER:OFF
MODE:ALL_CONTINUOUS_ROTATION
```

## Command Protocol

### Movement Commands
Format: `S[servo_num],[+/-][duration_ms]`

**Examples:**
```
S2,+200    # Move servo 2 clockwise for 200ms
S2,-150    # Move servo 2 counter-clockwise for 150ms
S3,+300    # Move servo 3 clockwise for 300ms
```

**Parameters:**
- `servo_num`: 1-4
- `+`: Clockwise direction
- `-`: Counter-clockwise direction
- `duration_ms`: Movement duration (1-5000 milliseconds)

### Other Commands
```
LOCKDOWN    # Lock door and window (S1 & S4 CW for 2500ms)
UNLOCK      # Unlock door and window (S1 & S4 CCW for 2500ms)
FIRE        # Fire shooter (500ms pulse)
STOP_ALL    # Emergency stop all servos
```

## Testing the Firmware

### Manual Test (Arduino Serial Monitor)

1. Open Serial Monitor at 9600 baud
2. Try these commands:

```
S2,+200     # Pan right for 200ms
S2,-200     # Pan left for 200ms
S3,+200     # Tilt down for 200ms
S3,-200     # Tilt up for 200ms
LOCKDOWN    # Lock doors
UNLOCK      # Unlock doors
STOP_ALL    # Emergency stop
```

### Python Test

```bash
cd Services/Interior_Watch
python turret_controller_continuous.py
```

Enter your serial port when prompted. The script will run a series of tests.

## Integrating with TheftDetectionSystem

### Option 1: Replace turret_controller.py (Recommended)

Backup the original and replace:
```bash
cd Services/Interior_Watch
mv turret_controller.py turret_controller_positional_backup.py
cp turret_controller_continuous.py turret_controller.py
```

### Option 2: Modify main.py

Update `main.py` to import the continuous version:
```python
# Change this line:
from turret_controller import TurretController

# To this:
from turret_controller_continuous import TurretControllerContinuous as TurretController
```

## Configuration with start_sentinel.py

Same environment variables work:

**Linux/macOS:**
```bash
export ARDUINO_PORT=/dev/ttyUSB0
python3 Sentinel_Unified/start_sentinel.py
```

**Windows:**
```cmd
set ARDUINO_PORT=COM11
python Sentinel_Unified\start_sentinel.py
```

**Or in `.env` file:**
```
ARDUINO_PORT=/dev/ttyUSB0
ARDUINO_BAUDRATE=9600
```

## Key Differences from Positional Servos

### Positional Servos (Original)
- Command: `S2,90` → Move to 90°
- Servo holds position
- Absolute positioning
- No timing needed

### Continuous Rotation Servos (New)
- Command: `S2,+200` → Rotate CW for 200ms
- Servo stops after duration
- Relative movement
- Timing critical

## Visual Servoing Behavior

The `TurretControllerContinuous` class adapts visual servoing for continuous rotation:

1. **Calculate error** from frame center
2. **Determine direction** (CW or CCW)
3. **Calculate duration** proportional to error
4. **Send timed movement command**
5. **Servo auto-stops** after duration

**Example:**
- Target 100 pixels to the right → Send `S2,+200` (pan CW for 200ms)
- Target 50 pixels to the left → Send `S2,-100` (pan CCW for 100ms)

## Calibration Tips

### Adjusting Movement Speed

In `turret_controller_continuous.py`, modify these parameters:

```python
# Movement parameters (milliseconds)
self.pan_step_duration = 200    # Increase for slower movements
self.tilt_step_duration = 200   # Decrease for faster movements
```

### Adjusting Responsiveness

In `calculate_correction()`:

```python
# Duration proportional to error
pan_duration = min(int(abs(error_x) * 2), 500)  # Change multiplier (2)
```

- **Higher multiplier** = More aggressive tracking
- **Lower multiplier** = Smoother, slower tracking

### Adjusting Dead Zone

```python
dead_zone = 20  # Increase to reduce jitter, decrease for tighter tracking
```

## Troubleshooting

### Servos Spin Continuously
- **Cause**: Command sent but not stopped
- **Fix**: Send `STOP_ALL` command
- **Prevention**: Ensure Arduino firmware is running the correct sketch

### Servos Don't Move
- **Check**: Uploaded correct firmware (`arduino_servo_controller_all_continuous.ino`)
- **Check**: Using correct command format (`S2,+200` not `S2,200`)
- **Check**: Power supply adequate for continuous rotation servos

### Tracking is Jerky
- **Increase** dead zone (reduce sensitivity)
- **Decrease** duration multiplier (smaller movements)
- **Add** delay between commands in tracking loop

### Turret Drifts Off Center
- **Expected**: Continuous rotation servos don't maintain absolute position
- **Solution**: Periodic re-centering based on visual feedback
- **Workaround**: Add limit switches for position reference

## Advanced: Position Estimation

Since continuous rotation servos don't provide position feedback, the Python driver maintains estimated state:

```python
self.estimated_pan_center = True   # Estimate if centered
self.estimated_tilt_center = True
```

For more accurate positioning:
1. Add encoders to servos
2. Add limit switches at known positions
3. Use visual markers in frame for position reference

## Comparison Table

| Feature | Positional Servos | Continuous Rotation |
|---------|------------------|---------------------|
| Command | `S2,90` (angle) | `S2,+200` (time) |
| Control | Absolute position | Timed movement |
| Holding | Holds position | Must send stop |
| Precision | High (±1°) | Lower (depends on timing) |
| Feedback | Position known | Position estimated |
| Speed Control | No | Yes (via PWM value) |
| Use Case | Pan/Tilt aiming | Continuous rotation needs |

## Summary

**For systems with ALL continuous rotation servos:**
1. Upload `arduino_servo_controller_all_continuous.ino`
2. Use `turret_controller_continuous.py` as driver
3. Commands use timed movements: `S2,+200`
4. System automatically stops servos after duration
5. Position is estimated, not absolute

This configuration works well for continuous rotation hardware while maintaining the same high-level API for the theft detection system.
