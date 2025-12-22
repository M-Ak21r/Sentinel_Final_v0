# Active Defense Turret Configuration

## Environment Variables

To enable the active defense turret system when running `start_sentinel.py`, you need to set the `ARDUINO_PORT` environment variable.

### Windows

```cmd
set ARDUINO_PORT=COM11
set ARDUINO_BAUDRATE=9600
python Sentinel_Unified/start_sentinel.py
```

Or add to `.env` file in project root:
```
ARDUINO_PORT=COM11
ARDUINO_BAUDRATE=9600
```

### Linux/macOS

```bash
export ARDUINO_PORT=/dev/ttyUSB0
export ARDUINO_BAUDRATE=9600
python3 Sentinel_Unified/start_sentinel.py
```

Or add to `.env` file in project root:
```
ARDUINO_PORT=/dev/ttyUSB0
ARDUINO_BAUDRATE=9600
```

## Finding Your Arduino Port

### Windows
- Open Device Manager → Ports (COM & LPT)
- Look for "Arduino" or "USB Serial Device"
- Note the COM port number (e.g., COM3, COM11)

### Linux
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Usually /dev/ttyUSB0 or /dev/ttyACM0
```

### macOS
```bash
ls /dev/tty.usb*
# Usually /dev/tty.usbserial or /dev/tty.usbmodem*
```

## Verifying Turret is Enabled

When you run `start_sentinel.py`, look for these messages in the Interior Watch service logs:

### Enabled (Turret Working):
```
[INTERIOR] Active Defense System: ENABLED (Port: COM11)
[INTERIOR] TurretController initialized successfully
```

### Disabled (No Arduino):
```
[INTERIOR] Active Defense System: DISABLED (No Arduino port specified)
[INTERIOR] Set ARDUINO_PORT environment variable to enable turret
```

## Testing the Turret

Run the diagnostic script to test your configuration:

```bash
cd Sentinel_Unified/Services/Interior_Watch
python test_turret.py [your_port]

# Examples:
python test_turret.py COM11           # Windows
python test_turret.py /dev/ttyUSB0    # Linux
```

## Troubleshooting

If turret doesn't work:

1. **Check Arduino is connected**: Verify USB cable is plugged in
2. **Upload firmware**: Ensure `arduino_servo_controller.ino` is uploaded to Arduino
3. **Check permissions (Linux)**: `sudo usermod -a -G dialout $USER` (logout/login required)
4. **Verify baud rate**: Must be 9600 (set in Arduino sketch)
5. **Test manually**: Use Arduino Serial Monitor at 9600 baud, type `S2,90` and press Enter

## Quick Start

1. Set environment variable:
   ```bash
   export ARDUINO_PORT=/dev/ttyUSB0  # Linux
   # or
   set ARDUINO_PORT=COM11  # Windows
   ```

2. Run Sentinel:
   ```bash
   python3 Sentinel_Unified/start_sentinel.py
   ```

3. Check logs for "Active Defense System: ENABLED"

4. System will automatically:
   - Track confirmed thieves
   - Center them in frame
   - Fire geotag marker when centered
   - Engage lockdown on theft detection
