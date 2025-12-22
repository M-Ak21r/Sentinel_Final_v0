#!/usr/bin/env python3
"""
TurretController for All Continuous Rotation Servos
====================================================
Adapter for controlling turret when ALL servos are continuous rotation type.

This version uses timed movements instead of position commands.
Works with arduino_servo_controller_all_continuous.ino firmware.

Author: Sentinel System
"""

import serial
import time
import logging

logger = logging.getLogger(__name__)


class TurretControllerContinuous:
    """
    Turret controller for systems with all continuous rotation servos.
    
    Instead of positioning servos at specific angles, this controller
    sends timed movement commands (move CW/CCW for X milliseconds).
    """
    
    def __init__(self, serial_port='COM11', baud_rate=9600):
        """
        Initialize the turret controller for continuous rotation servos.
        
        Args:
            serial_port: Serial port for Arduino (e.g., 'COM11', '/dev/ttyUSB0')
            baud_rate: Baud rate for serial communication (default: 9600)
        """
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.serial_connection = None
        
        # Movement parameters (milliseconds)
        self.pan_step_duration = 200    # Time for one pan adjustment
        self.tilt_step_duration = 200   # Time for one tilt adjustment
        
        # Tracking state (estimated, not absolute)
        self.estimated_pan_center = True
        self.estimated_tilt_center = True
        
        # Initialize serial connection
        if serial_port:
            try:
                self.serial_connection = serial.Serial(
                    serial_port,
                    baud_rate,
                    timeout=1
                )
                logger.info(f"Serial connection opened on {serial_port}")
                
                # Wait for Arduino reset
                time.sleep(2)
                
                # Read startup messages
                logger.info("Arduino startup messages:")
                time.sleep(0.5)
                while self.serial_connection.in_waiting > 0:
                    msg = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if msg:
                        logger.info(f"  {msg}")
                
                logger.info("TurretControllerContinuous initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize turret controller: {e}")
                self.serial_connection = None
        else:
            logger.warning("No serial port specified, turret controller disabled")
    
    def _send_command(self, command):
        """
        Send command to Arduino.
        
        Args:
            command: Command string to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.serial_connection is None:
            return False
        
        try:
            self.serial_connection.write(f"{command}\n".encode('utf-8'))
            self.serial_connection.flush()
            
            # Wait for response
            time.sleep(0.1)
            if self.serial_connection.in_waiting > 0:
                response = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                logger.debug(f"Command: {command} → Response: {response}")
                return "ACK" in response
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            return False
    
    def calculate_correction(self, target_center_x, target_center_y, frame_width, frame_height):
        """
        Calculate movement direction and duration for continuous rotation servos.
        
        Args:
            target_center_x: X coordinate of target center
            target_center_y: Y coordinate of target center  
            frame_width: Width of frame
            frame_height: Height of frame
            
        Returns:
            tuple: (pan_direction, pan_duration, tilt_direction, tilt_duration)
                   direction: 1 for CW, -1 for CCW, 0 for no movement
                   duration: milliseconds to move
        """
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2
        
        # Calculate errors
        error_x = target_center_x - frame_center_x
        error_y = target_center_y - frame_center_y
        
        # Dead zone to prevent jitter
        dead_zone = 20
        
        # Pan correction
        if abs(error_x) < dead_zone:
            pan_direction = 0
            pan_duration = 0
        else:
            # Determine direction: target right of center -> move CW
            pan_direction = 1 if error_x > 0 else -1
            # Duration proportional to error (capped)
            pan_duration = min(int(abs(error_x) * 2), 500)
        
        # Tilt correction  
        if abs(error_y) < dead_zone:
            tilt_direction = 0
            tilt_duration = 0
        else:
            # Determine direction: target below center -> move CW
            tilt_direction = 1 if error_y > 0 else -1
            # Duration proportional to error (capped)
            tilt_duration = min(int(abs(error_y) * 2), 500)
        
        return (pan_direction, pan_duration, tilt_direction, tilt_duration)
    
    def track_target(self, bbox, frame_shape):
        """
        Track target using timed movements.
        
        Args:
            bbox: Bounding box (x, y, width, height)
            frame_shape: Frame shape (height, width, channels)
            
        Returns:
            bool: True if commands sent successfully
        """
        if self.serial_connection is None:
            return False
        
        try:
            # Extract bbox center
            bbox_x, bbox_y, bbox_w, bbox_h = bbox
            target_center_x = bbox_x + bbox_w / 2
            target_center_y = bbox_y + bbox_h / 2
            
            frame_height, frame_width = frame_shape[:2]
            
            # Calculate corrections
            pan_dir, pan_dur, tilt_dir, tilt_dur = self.calculate_correction(
                target_center_x, target_center_y, frame_width, frame_height
            )
            
            # Send movement commands
            success = True
            
            if pan_dir != 0 and pan_dur > 0:
                sign = '+' if pan_dir > 0 else '-'
                command = f"S2,{sign}{pan_dur}"
                success = success and self._send_command(command)
            
            if tilt_dir != 0 and tilt_dur > 0:
                sign = '+' if tilt_dir > 0 else '-'
                command = f"S3,{sign}{tilt_dur}"
                success = success and self._send_command(command)
            
            return success
            
        except Exception as e:
            logger.error(f"Error tracking target: {e}")
            return False
    
    def move_pan(self, direction, duration_ms=200):
        """
        Move pan servo.
        
        Args:
            direction: 1 for CW, -1 for CCW
            duration_ms: Movement duration in milliseconds
            
        Returns:
            bool: True if successful
        """
        sign = '+' if direction > 0 else '-'
        command = f"S2,{sign}{duration_ms}"
        return self._send_command(command)
    
    def move_tilt(self, direction, duration_ms=200):
        """
        Move tilt servo.
        
        Args:
            direction: 1 for CW, -1 for CCW
            duration_ms: Movement duration in milliseconds
            
        Returns:
            bool: True if successful
        """
        sign = '+' if direction > 0 else '-'
        command = f"S3,{sign}{duration_ms}"
        return self._send_command(command)
    
    def center_turret(self):
        """
        Attempt to center turret (not precise with continuous rotation).
        
        This is a best-effort approximation.
        
        Returns:
            bool: True if successful
        """
        logger.info("Centering turret (approximate)")
        # Since we can't know absolute position, just mark as centered
        self.estimated_pan_center = True
        self.estimated_tilt_center = True
        return True
    
    def engage_lockdown(self):
        """
        Engage lockdown (lock door and window).
        
        Returns:
            bool: True if successful
        """
        logger.info("Engaging lockdown")
        return self._send_command("LOCKDOWN")
    
    def disengage_lockdown(self):
        """
        Disengage lockdown (unlock door and window).
        
        Returns:
            bool: True if successful
        """
        logger.info("Disengaging lockdown")
        return self._send_command("UNLOCK")
    
    def shoot(self):
        """
        Fire shooter mechanism.
        
        Returns:
            bool: True if successful
        """
        logger.warning("FIRING SHOOTER")
        return self._send_command("FIRE")
    
    def stop_all(self):
        """
        Emergency stop all servos.
        
        Returns:
            bool: True if successful
        """
        logger.warning("EMERGENCY STOP ALL SERVOS")
        return self._send_command("STOP_ALL")
    
    def test_connection(self):
        """
        Test Arduino connection.
        
        Returns:
            bool: True if Arduino responds
        """
        if self.serial_connection is None:
            logger.error("Cannot test connection: Serial port not connected")
            return False
        
        try:
            logger.info("Testing Arduino connection...")
            
            # Clear buffer
            self.serial_connection.reset_input_buffer()
            
            # Send test command
            self.serial_connection.write(b"S2,+100\n")
            self.serial_connection.flush()
            
            # Wait for response
            time.sleep(0.2)
            
            if self.serial_connection.in_waiting > 0:
                response = self.serial_connection.readline().decode('utf-8').strip()
                logger.info(f"Arduino responded: {response}")
                
                if "ACK" in response:
                    logger.info("✓ Arduino connection test PASSED")
                    return True
                else:
                    logger.warning(f"Unexpected response: {response}")
                    return False
            else:
                logger.error("✗ No response from Arduino")
                return False
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def cleanup(self):
        """Close serial connection."""
        try:
            logger.info("Cleaning up turret controller")
            
            # Stop all servos
            if self.serial_connection is not None:
                try:
                    self._send_command("STOP_ALL")
                except:
                    pass
            
            # Close serial connection
            if self.serial_connection is not None:
                try:
                    self.serial_connection.close()
                    logger.info("Serial connection closed")
                except Exception as e:
                    logger.warning(f"Error closing serial connection: {e}")
                self.serial_connection = None
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    # Test harness
    logging.basicConfig(level=logging.INFO)
    
    print("TurretControllerContinuous Test Harness")
    print("="*50)
    
    port = input("Enter serial port (e.g., COM11 or /dev/ttyUSB0): ")
    
    turret = TurretControllerContinuous(serial_port=port)
    
    if turret.serial_connection:
        print("\nTesting connection...")
        turret.test_connection()
        
        print("\nTest 1: Move pan CW for 200ms")
        turret.move_pan(1, 200)
        time.sleep(1)
        
        print("\nTest 2: Move pan CCW for 200ms")
        turret.move_pan(-1, 200)
        time.sleep(1)
        
        print("\nTest 3: Move tilt CW for 200ms")
        turret.move_tilt(1, 200)
        time.sleep(1)
        
        print("\nTest 4: Move tilt CCW for 200ms")
        turret.move_tilt(-1, 200)
        time.sleep(1)
        
        print("\nTest 5: LOCKDOWN")
        turret.engage_lockdown()
        time.sleep(3)
        
        print("\nTest 6: UNLOCK")
        turret.disengage_lockdown()
        time.sleep(3)
        
        print("\nTest 7: Stop all")
        turret.stop_all()
        
        print("\nCleaning up...")
        turret.cleanup()
    else:
        print("Failed to initialize turret controller")
