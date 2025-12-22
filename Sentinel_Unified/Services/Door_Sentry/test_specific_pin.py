#!/usr/bin/env python3
"""
Test Servo on Specific Pin
===========================
Tests servo connected to Arduino with proper commands for each pin type.

Usage:
    python test_specific_pin.py [port] [pin_number]

Examples:
    python test_specific_pin.py COM11 10         # Windows, Pin 10
    python test_specific_pin.py /dev/ttyUSB0 9   # Linux, Pin 9
"""

import sys
import serial
import time

def test_pin_10_continuous_rotation(port):
    """Test Pin 10 (S1) with LOCKDOWN/UNLOCK commands."""
    print("\n" + "="*60)
    print("Testing Pin 10 (S1 - Door Lock)")
    print("Type: Continuous Rotation Servo")
    print("="*60)
    
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"✓ Opened {port}")
        
        print("\nWaiting for Arduino reset (2 seconds)...")
        time.sleep(2)
        
        # Read startup messages
        while ser.in_waiting > 0:
            msg = ser.readline().decode('utf-8', errors='ignore').strip()
            if msg:
                print(f"  Arduino: {msg}")
        
        print("\n" + "-"*60)
        print("Test 1: LOCKDOWN command")
        print("-"*60)
        print("Servo should spin CLOCKWISE for 2.5 seconds, then STOP")
        input("Press Enter to send LOCKDOWN command...")
        
        ser.write(b"LOCKDOWN\n")
        time.sleep(0.1)
        
        # Read response
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8', errors='ignore').strip()
            print(f"  Response: {response}")
        
        print("Waiting 3 seconds (servo should stop after 2.5s)...")
        time.sleep(3)
        
        print("\n" + "-"*60)
        print("Test 2: UNLOCK command")
        print("-"*60)
        print("Servo should spin COUNTER-CLOCKWISE for 2.5 seconds, then STOP")
        input("Press Enter to send UNLOCK command...")
        
        ser.write(b"UNLOCK\n")
        time.sleep(0.1)
        
        # Read response
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8', errors='ignore').strip()
            print(f"  Response: {response}")
        
        print("Waiting 3 seconds (servo should stop after 2.5s)...")
        time.sleep(3)
        
        ser.close()
        
        print("\n" + "="*60)
        print("✓ Test complete")
        print("="*60)
        print("\nDid the servo move?")
        print("  YES → Servo is working correctly with LOCKDOWN/UNLOCK")
        print("  NO  → Check:")
        print("        - Servo power supply (needs 5V + enough current)")
        print("        - Servo connections (signal, power, ground)")
        print("        - Servo type (should be continuous rotation or will")
        print("          rotate continuously with these commands)")
        
    except serial.SerialException as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_pin_9_positional(port):
    """Test Pin 9 (S2) with angle commands."""
    print("\n" + "="*60)
    print("Testing Pin 9 (S2 - Pan/Tilt)")
    print("Type: Positional Servo (0-180°)")
    print("="*60)
    
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"✓ Opened {port}")
        
        print("\nWaiting for Arduino reset (2 seconds)...")
        time.sleep(2)
        
        # Read startup messages
        while ser.in_waiting > 0:
            msg = ser.readline().decode('utf-8', errors='ignore').strip()
            if msg:
                print(f"  Arduino: {msg}")
        
        angles = [0, 90, 180, 90]
        labels = ["Minimum (0°)", "Center (90°)", "Maximum (180°)", "Center (90°)"]
        
        for angle, label in zip(angles, labels):
            print("\n" + "-"*60)
            print(f"Test: Move to {label}")
            print("-"*60)
            input(f"Press Enter to move servo to {angle}°...")
            
            command = f"S2,{angle}\n"
            ser.write(command.encode())
            time.sleep(0.1)
            
            # Read response
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"  Response: {response}")
            
            print(f"Servo should now be at {angle}°")
            time.sleep(1)
        
        ser.close()
        
        print("\n" + "="*60)
        print("✓ Test complete")
        print("="*60)
        print("\nDid the servo move to all positions?")
        print("  YES → Servo is working correctly!")
        print("  NO  → Check:")
        print("        - Servo power supply (needs 5V + enough current)")
        print("        - Servo connections (signal to Pin 9, power, ground)")
        print("        - Servo type (should be standard positional servo)")
        
    except serial.SerialException as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_pin_11_positional(port):
    """Test Pin 11 (S3) with angle commands."""
    print("\n" + "="*60)
    print("Testing Pin 11 (S3 - Pan/Tilt)")
    print("Type: Positional Servo (0-180°)")
    print("="*60)
    
    try:
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"✓ Opened {port}")
        
        print("\nWaiting for Arduino reset (2 seconds)...")
        time.sleep(2)
        
        # Read startup messages
        while ser.in_waiting > 0:
            msg = ser.readline().decode('utf-8', errors='ignore').strip()
            if msg:
                print(f"  Arduino: {msg}")
        
        angles = [0, 90, 180, 90]
        labels = ["Minimum (0°)", "Center (90°)", "Maximum (180°)", "Center (90°)"]
        
        for angle, label in zip(angles, labels):
            print("\n" + "-"*60)
            print(f"Test: Move to {label}")
            print("-"*60)
            input(f"Press Enter to move servo to {angle}°...")
            
            command = f"S3,{angle}\n"
            ser.write(command.encode())
            time.sleep(0.1)
            
            # Read response
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"  Response: {response}")
            
            print(f"Servo should now be at {angle}°")
            time.sleep(1)
        
        ser.close()
        
        print("\n" + "="*60)
        print("✓ Test complete")
        print("="*60)
        print("\nDid the servo move to all positions?")
        print("  YES → Servo is working correctly!")
        print("  NO  → Check:")
        print("        - Servo power supply (needs 5V + enough current)")
        print("        - Servo connections (signal to Pin 11, power, ground)")
        print("        - Servo type (should be standard positional servo)")
        
    except serial.SerialException as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    """Main test routine."""
    print("="*60)
    print("Servo Pin Test Tool")
    print("="*60)
    
    # Get port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        import platform
        system = platform.system()
        if system == "Windows":
            port = "COM11"
        else:
            port = "/dev/ttyUSB0"
        print(f"No port specified, using default: {port}")
    
    # Get pin number
    if len(sys.argv) > 2:
        pin = int(sys.argv[2])
    else:
        print("\nWhich pin is your servo connected to?")
        print("  10 - S1 (Door Lock - Continuous Rotation)")
        print("  9  - S2 (Pan - Positional)")
        print("  11 - S3 (Tilt - Positional)")
        print("  6  - S4 (Window Lock - Continuous Rotation)")
        pin = int(input("\nEnter pin number: "))
    
    # Run appropriate test
    if pin == 10:
        test_pin_10_continuous_rotation(port)
    elif pin == 9:
        test_pin_9_positional(port)
    elif pin == 11:
        test_pin_11_positional(port)
    elif pin == 6:
        print("\nPin 6 (S4) is also a continuous rotation servo.")
        print("It uses the same LOCKDOWN/UNLOCK commands as Pin 10.")
        test_pin_10_continuous_rotation(port)
    else:
        print(f"\n✗ Error: Pin {pin} is not configured in the firmware")
        print("Available pins: 9 (S2), 10 (S1), 11 (S3), 6 (S4)")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
