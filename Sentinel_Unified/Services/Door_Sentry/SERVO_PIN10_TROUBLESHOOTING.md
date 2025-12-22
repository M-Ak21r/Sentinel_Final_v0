# Servo Pin 10 Troubleshooting Guide

## Issue: Servo on Pin 10 Not Moving

Pin 10 (SERVO1_PIN) is configured as a **Continuous Rotation Servo** for the door lock mechanism. This is different from regular positional servos.

### Understanding Pin 10 Behavior

**Pin 10 (S1 - Door Lock):**
- Type: Continuous Rotation Servo
- Commands: `LOCKDOWN` or `UNLOCK` only
- Direct `S1,angle` commands will return: `ERR:USE_LOCKDOWN_OR_UNLOCK`
- On startup: Stopped at 90° (SERVO_STOP)

### Testing Pin 10 (Door Lock Servo)

#### Method 1: Use LOCKDOWN/UNLOCK Commands

```
# In Arduino Serial Monitor (9600 baud):
LOCKDOWN    # Servo spins CW for 2.5 seconds, then stops
UNLOCK      # Servo spins CCW for 2.5 seconds, then stops
```

#### Method 2: Test with Positional Servo Pins

If you have a **regular positional servo** (not continuous rotation), connect it to:
- **Pin 9 (S2 - Pan)** - Responds to `S2,angle`
- **Pin 11 (S3 - Tilt)** - Responds to `S3,angle`

Example:
```
S2,0      # Move to 0 degrees
S2,90     # Move to 90 degrees (center)
S2,180    # Move to 180 degrees
```

### Quick Diagnostic

**Test each pin:**

```bash
# Connect servo to Pin 9 and test:
S2,45
S2,135
S2,90

# Connect servo to Pin 11 and test:
S3,45
S3,135
S3,90

# Connect continuous rotation servo to Pin 10 and test:
LOCKDOWN
# Wait 2.5 seconds, servo should stop
UNLOCK
# Wait 2.5 seconds, servo should stop
```

### If You Want Pin 10 to Work Like a Regular Servo

You need to modify the Arduino firmware to treat S1 as a positional servo instead of continuous rotation.

**Option 1: Use the Simple Test Sketch (Recommended for Testing)**

Upload this minimal test sketch to verify your servo works:

```cpp
#include <Servo.h>

Servo testServo;

void setup() {
  Serial.begin(9600);
  testServo.attach(10);  // Pin 10
  testServo.write(90);   // Center position
  Serial.println("Servo attached to pin 10");
  Serial.println("Send angle 0-180");
}

void loop() {
  if (Serial.available() > 0) {
    int angle = Serial.parseInt();
    if (angle >= 0 && angle <= 180) {
      testServo.write(angle);
      Serial.print("Moved to: ");
      Serial.println(angle);
    }
  }
}
```

**Option 2: Modify the Full Firmware**

See `CONVERT_S1_TO_POSITIONAL.md` for instructions on modifying the firmware to treat S1 as a positional servo.

### Hardware Checklist

If servo still doesn't move:

1. **Power Supply:**
   - Servos need 5V and sufficient current (500mA+ per servo)
   - Arduino USB power may not be enough for multiple servos
   - Use external 5V power supply connected to servo power/ground

2. **Connections:**
   - Signal wire (usually orange/yellow) → Pin 10
   - Power wire (usually red) → 5V or external power
   - Ground wire (usually brown/black) → GND (shared with Arduino)

3. **Servo Type:**
   - Verify it's a standard hobby servo (not continuous rotation)
   - Should have 3 wires
   - Should respond to 0-180 degree commands

4. **Arduino:**
   - Verify sketch is uploaded (check for "SERVO_READY" in Serial Monitor)
   - Try different USB cable
   - Try different USB port

### Expected vs Actual Behavior

**If using test_turret.py:**

The script sends `S2,90` commands (Pin 9), NOT `S1` commands (Pin 10).

**For Pin 10 testing with current firmware:**
```python
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
time.sleep(2)

# This will work for Pin 10 (continuous rotation):
ser.write(b"LOCKDOWN\n")
time.sleep(3)  # Watch servo spin for 2.5 seconds
ser.write(b"UNLOCK\n")
time.sleep(3)  # Watch servo spin opposite direction

ser.close()
```

**For Pin 9 or 11 testing (positional servos):**
```python
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
time.sleep(2)

# Test Pin 9 (S2):
ser.write(b"S2,0\n")
time.sleep(1)
ser.write(b"S2,180\n")
time.sleep(1)
ser.write(b"S2,90\n")

ser.close()
```

### Summary

- **Pin 10 (S1)**: Continuous rotation servo, use `LOCKDOWN`/`UNLOCK`
- **Pin 9 (S2)**: Positional servo, use `S2,angle`
- **Pin 11 (S3)**: Positional servo, use `S3,angle`
- **Pin 6 (S4)**: Continuous rotation servo, use `LOCKDOWN`/`UNLOCK`

For testing a regular servo, **use Pin 9 or Pin 11** with the current firmware.
