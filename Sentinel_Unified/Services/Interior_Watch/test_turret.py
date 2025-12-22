#!/usr/bin/env python3
"""
Turret Diagnostic and Test Script
==================================
This script helps diagnose connection and servo issues with the turret system.

Usage:
    python test_turret.py [serial_port]

Examples:
    python test_turret.py COM11           # Windows
    python test_turret.py /dev/ttyUSB0    # Linux
    python test_turret.py /dev/ttyACM0    # Linux (alternate)
"""

import sys
import time
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_serial_port_availability(port):
    """Test if serial port exists and is accessible."""
    try:
        import serial
        logger.info(f"Testing serial port: {port}")
        
        # Try to open the port
        ser = serial.Serial(port, 9600, timeout=1)
        logger.info(f"✓ Successfully opened {port}")
        ser.close()
        return True
        
    except serial.SerialException as e:
        logger.error(f"✗ Cannot open {port}: {e}")
        logger.error("Common fixes:")
        logger.error("  - Check if Arduino is connected")
        logger.error("  - Try a different USB port")
        logger.error("  - On Linux: sudo usermod -a -G dialout $USER (then logout/login)")
        logger.error("  - Check if another program is using the port")
        return False
    except ImportError:
        logger.error("✗ pyserial not installed. Run: pip install pyserial")
        return False

def test_arduino_communication(port):
    """Test basic communication with Arduino."""
    try:
        import serial
        
        logger.info("Opening serial connection...")
        ser = serial.Serial(port, 9600, timeout=1)
        
        logger.info("Waiting for Arduino reset (2 seconds)...")
        time.sleep(2)
        
        # Read startup messages
        logger.info("Reading Arduino startup messages:")
        startup_messages = []
        time.sleep(0.5)
        
        while ser.in_waiting > 0:
            try:
                msg = ser.readline().decode('utf-8').strip()
                logger.info(f"  Arduino: {msg}")
                startup_messages.append(msg)
            except:
                pass
        
        if not startup_messages:
            logger.warning("⚠ No startup messages received from Arduino")
            logger.warning("Possible issues:")
            logger.warning("  - Wrong baud rate (should be 9600)")
            logger.warning("  - Arduino sketch not uploaded")
            logger.warning("  - USB cable is power-only (no data lines)")
            return False
        
        if "SERVO_READY" in ' '.join(startup_messages):
            logger.info("✓ Arduino firmware is running correctly")
        else:
            logger.warning("⚠ Expected 'SERVO_READY' message not found")
        
        # Clear input buffer
        ser.reset_input_buffer()
        
        # Test pan servo command
        logger.info("\nTesting Pan servo (S2)...")
        ser.write(b"S2,45\n")
        time.sleep(0.2)
        
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            logger.info(f"  Response: {response}")
            
            if "ACK:S2:45" in response:
                logger.info("  ✓ Pan servo command acknowledged")
            else:
                logger.warning(f"  ⚠ Unexpected response: {response}")
        else:
            logger.error("  ✗ No response from Arduino")
        
        # Test tilt servo command
        logger.info("\nTesting Tilt servo (S3)...")
        ser.write(b"S3,135\n")
        time.sleep(0.2)
        
        if ser.in_waiting > 0:
            response = ser.readline().decode('utf-8').strip()
            logger.info(f"  Response: {response}")
            
            if "ACK:S3:135" in response:
                logger.info("  ✓ Tilt servo command acknowledged")
            else:
                logger.warning(f"  ⚠ Unexpected response: {response}")
        else:
            logger.error("  ✗ No response from Arduino")
        
        # Re-center
        logger.info("\nRe-centering servos...")
        ser.write(b"S2,90\n")
        time.sleep(0.2)
        ser.write(b"S3,90\n")
        time.sleep(0.2)
        
        ser.close()
        logger.info("\n✓ Communication test complete")
        return True
        
    except Exception as e:
        logger.error(f"Communication test failed: {e}")
        return False

def test_turret_controller(port):
    """Test TurretController class."""
    try:
        logger.info("\nTesting TurretController class...")
        
        from turret_controller import TurretController
        
        logger.info(f"Initializing TurretController on {port}...")
        turret = TurretController(serial_port=port, baud_rate=9600)
        
        if turret.serial_connection is None:
            logger.error("✗ TurretController failed to connect")
            return False
        
        logger.info("✓ TurretController initialized")
        
        # Test connection
        logger.info("\nRunning connection test...")
        if turret.test_connection():
            logger.info("✓ Connection test passed")
        else:
            logger.error("✗ Connection test failed")
        
        # Test centering
        logger.info("\nTesting center_turret()...")
        if turret.center_turret():
            logger.info("✓ Turret centered successfully")
        else:
            logger.warning("⚠ Center command may have failed")
        
        time.sleep(1)
        
        # Test tracking simulation
        logger.info("\nTesting track_target() with simulated bbox...")
        # Target to the right
        result = turret.track_target((400, 240, 50, 50), (480, 640, 3))
        if result:
            logger.info(f"✓ Track command sent, new position: {result}")
        else:
            logger.warning("⚠ Track command may have failed")
        
        time.sleep(1)
        
        # Re-center
        logger.info("\nRe-centering before cleanup...")
        turret.center_turret()
        
        time.sleep(0.5)
        
        # Cleanup
        logger.info("\nCleaning up...")
        turret.cleanup()
        
        logger.info("✓ TurretController test complete")
        return True
        
    except ImportError as e:
        logger.error(f"Cannot import TurretController: {e}")
        logger.error("Make sure you're running from the correct directory")
        return False
    except Exception as e:
        logger.error(f"TurretController test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main diagnostic routine."""
    print("=" * 60)
    print("Turret System Diagnostic Tool")
    print("=" * 60)
    
    # Determine serial port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        # Try to auto-detect
        import platform
        system = platform.system()
        
        if system == "Windows":
            port = "COM11"
        elif system == "Linux":
            port = "/dev/ttyUSB0"
        elif system == "Darwin":  # macOS
            port = "/dev/tty.usbserial"
        else:
            port = "COM11"
        
        logger.info(f"No port specified, using default: {port}")
        logger.info(f"To specify: python {sys.argv[0]} <port>")
    
    print()
    
    # Run tests
    tests_passed = 0
    tests_total = 3
    
    print("\n" + "-" * 60)
    print("Test 1: Serial Port Availability")
    print("-" * 60)
    if test_serial_port_availability(port):
        tests_passed += 1
    
    print("\n" + "-" * 60)
    print("Test 2: Arduino Communication")
    print("-" * 60)
    if test_arduino_communication(port):
        tests_passed += 1
    
    print("\n" + "-" * 60)
    print("Test 3: TurretController Class")
    print("-" * 60)
    if test_turret_controller(port):
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"DIAGNOSTIC SUMMARY: {tests_passed}/{tests_total} tests passed")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("✓ All tests passed! Servos should be working.")
        print("\nIf servos still don't move:")
        print("  1. Check servo power supply (5V or external)")
        print("  2. Verify servo signal wires are connected to correct pins")
        print("  3. Test servos with Arduino Serial Monitor manually")
        return 0
    else:
        print("\n✗ Some tests failed. Review the error messages above.")
        print("\nCommon issues:")
        print("  - Wrong serial port")
        print("  - Arduino sketch not uploaded")
        print("  - Baud rate mismatch")
        print("  - Serial permissions (Linux)")
        print("  - USB cable issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
