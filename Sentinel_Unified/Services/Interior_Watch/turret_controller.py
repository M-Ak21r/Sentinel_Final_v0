"""
Turret Controller Module
========================
Controls the 2-axis turret (Pan/Tilt) and shooter mechanism via Arduino serial interface.

Implements visual servoing for automated target tracking with proportional control
and dead-zone filtering to prevent servo jitter.

Author: Sentinel System
"""

import serial
import time
import logging

# Configure logging
logger = logging.getLogger(__name__)


class TurretController:
    """Controller for 2-axis turret with pan/tilt servos and shooter mechanism.
    
    Communicates with Arduino firmware via serial commands to:
    - Control pan (S2) and tilt (S3) servos for target tracking
    - Engage/disengage lockdown mode (S1, S4 door/window locks)
    - Fire shooter mechanism
    
    Implements visual servoing with proportional control and dead-zone filtering.
    """
    
    # Visual servoing constants
    # Note: These are tuned for 640x480 frame size. Adjust for different resolutions.
    DEAD_ZONE_PIXELS = 20  # Minimum error to trigger correction (prevents jitter)
    PROPORTIONAL_GAIN = 0.1  # P-gain for error-to-angle conversion (tune as needed)
    
    def __init__(self, serial_port='COM11', baud_rate=9600):
        """Initialize turret controller with serial connection to Arduino.
        
        Args:
            serial_port: Serial port name (default 'COM11' for Windows,
                        use '/dev/ttyUSB0' or '/dev/ttyACM0' for Linux/macOS)
            baud_rate: Serial baud rate (default 9600)
        """
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.serial_connection = None
        
        # Current servo positions (center positions for pan/tilt)
        self.current_pan = 90
        self.current_tilt = 90
        
        # Initialize serial connection
        self._init_serial_connection()
        
    def _init_serial_connection(self):
        """Initialize serial connection to Arduino with error handling."""
        try:
            self.serial_connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1
            )
            # Wait for Arduino reset after serial connection
            time.sleep(2)
            logger.info(f"Turret controller connected on {self.serial_port} at {self.baud_rate} baud")
            
            # Read and log startup messages
            time.sleep(0.5)
            while self.serial_connection.in_waiting > 0:
                try:
                    msg = self.serial_connection.readline().decode('utf-8').strip()
                    logger.info(f"Arduino: {msg}")
                except Exception as e:
                    logger.debug(f"Error reading startup message: {e}")
                    
        except serial.SerialException as e:
            logger.warning(f"Could not establish serial connection: {e}. Running in simulation mode.")
            self.serial_connection = None
        except Exception as e:
            logger.warning(f"Unexpected error initializing serial: {e}. Running in simulation mode.")
            self.serial_connection = None
    
    def _send_command(self, command):
        """Send command to Arduino via serial connection.
        
        Args:
            command: Command string to send (will be terminated with \\n)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.serial_connection is None:
            logger.debug(f"Serial not connected. Simulated command: {command}")
            return False
        
        try:
            # Ensure command ends with newline
            if not command.endswith('\n'):
                command += '\n'
            
            self.serial_connection.write(command.encode('utf-8'))
            self.serial_connection.flush()
            logger.debug(f"Sent command: {command.strip()}")
            
            # Read acknowledgment if available
            time.sleep(0.05)  # Brief wait for ACK
            if self.serial_connection.in_waiting > 0:
                try:
                    ack = self.serial_connection.readline().decode('utf-8').strip()
                    logger.debug(f"Arduino ACK: {ack}")
                except Exception:
                    pass
            
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial communication error: {e}")
            self._handle_serial_disconnect()
            return False
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def _handle_serial_disconnect(self):
        """Handle serial disconnection gracefully."""
        logger.warning("Serial connection lost. Attempting to reconnect...")
        if self.serial_connection is not None:
            try:
                self.serial_connection.close()
            except Exception:
                pass
        self.serial_connection = None
        # Try to reconnect
        self._init_serial_connection()
    
    def calculate_correction(self, target_center_x, target_center_y, frame_width, frame_height):
        """Calculate pan/tilt corrections using visual servoing with proportional control.
        
        Implements a dead-zone to prevent servo jitter when target is near center.
        Uses proportional gain to convert pixel error to angle correction.
        
        Args:
            target_center_x: X coordinate of target center in pixels
            target_center_y: Y coordinate of target center in pixels
            frame_width: Width of frame in pixels
            frame_height: Height of frame in pixels
            
        Returns:
            tuple: (pan_correction, tilt_correction) in degrees
        """
        # Calculate frame center
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2
        
        # Calculate error (distance from center)
        error_x = target_center_x - frame_center_x
        error_y = target_center_y - frame_center_y
        
        # Apply dead zone to prevent jitter
        pan_correction = 0
        tilt_correction = 0
        
        if abs(error_x) > self.DEAD_ZONE_PIXELS:
            # Positive error_x means target is to the RIGHT of center
            # For standard servo mounting: lower angle pans right, higher angle pans left
            # Therefore, use negative gain to decrease angle when target is right
            # Note: May need sign adjustment based on actual servo mounting orientation
            pan_correction = -error_x * self.PROPORTIONAL_GAIN
        
        if abs(error_y) > self.DEAD_ZONE_PIXELS:
            # Positive error_y means target is BELOW center
            # For standard servo mounting: higher angle tilts down, lower angle tilts up
            # Note: May need sign adjustment based on actual servo mounting orientation
            tilt_correction = error_y * self.PROPORTIONAL_GAIN
        
        logger.debug(f"Error: X={error_x:.1f}px, Y={error_y:.1f}px | "
                    f"Correction: Pan={pan_correction:.1f}°, Tilt={tilt_correction:.1f}°")
        
        return pan_correction, tilt_correction
    
    def track_target(self, bbox, frame_shape):
        """Track target by adjusting pan/tilt servos to center it in frame.
        
        Extracts target center from bounding box, calculates corrections,
        and sends servo commands only if angles change.
        
        Args:
            bbox: Bounding box tuple (x, y, w, h) of target
            frame_shape: Frame shape tuple (height, width, channels)
            
        Returns:
            tuple: (new_pan_angle, new_tilt_angle) or None if tracking failed
        """
        try:
            # Extract bbox coordinates
            x, y, w, h = bbox
            
            # Calculate target center
            target_center_x = x + w / 2
            target_center_y = y + h / 2
            
            # Get frame dimensions
            frame_height, frame_width = frame_shape[:2]
            
            # Calculate corrections
            pan_correction, tilt_correction = self.calculate_correction(
                target_center_x, target_center_y, frame_width, frame_height
            )
            
            # Update angles
            new_pan = self.current_pan + pan_correction
            new_tilt = self.current_tilt + tilt_correction
            
            # Clamp angles to valid servo range (0-180)
            new_pan = max(0, min(180, int(new_pan)))
            new_tilt = max(0, min(180, int(new_tilt)))
            
            # Send commands only if angles changed
            pan_changed = (new_pan != self.current_pan)
            tilt_changed = (new_tilt != self.current_tilt)
            
            if pan_changed:
                if self._send_command(f"S2,{new_pan}"):
                    self.current_pan = new_pan
                    logger.info(f"Pan adjusted to {new_pan}°")
            
            if tilt_changed:
                if self._send_command(f"S3,{new_tilt}"):
                    self.current_tilt = new_tilt
                    logger.info(f"Tilt adjusted to {new_tilt}°")
            
            if not pan_changed and not tilt_changed:
                logger.debug("Target centered - no adjustment needed")
            
            return (new_pan, new_tilt)
            
        except Exception as e:
            logger.error(f"Error in track_target: {e}")
            return None
    
    def engage_lockdown(self):
        """Engage lockdown mode - locks door (S1) and window (S4) servos to 180°.
        
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        try:
            logger.warning("ENGAGING LOCKDOWN MODE")
            success = self._send_command("LOCKDOWN")
            if success:
                logger.info("Lockdown engaged - door and window locked")
            return success
        except Exception as e:
            logger.error(f"Error engaging lockdown: {e}")
            return False
    
    def disengage_lockdown(self):
        """Disengage lockdown mode - unlocks door (S1) and window (S4) servos to 0°.
        
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        try:
            logger.info("DISENGAGING LOCKDOWN MODE")
            success = self._send_command("UNLOCK")
            if success:
                logger.info("Lockdown disengaged - door and window unlocked")
            return success
        except Exception as e:
            logger.error(f"Error disengaging lockdown: {e}")
            return False
    
    def shoot(self):
        """Fire shooter mechanism - activates motors for 500ms pulse.
        
        Note: This command blocks for ~500ms during motor activation.
        
        Returns:
            bool: True if command sent successfully, False otherwise
        """
        try:
            logger.warning("FIRING SHOOTER")
            success = self._send_command("FIRE")
            if success:
                logger.info("Shooter fired")
            return success
        except Exception as e:
            logger.error(f"Error firing shooter: {e}")
            return False
    
    def center_turret(self):
        """Reset turret to center position (90° pan, 90° tilt).
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Centering turret")
            pan_success = self._send_command("S2,90")
            tilt_success = self._send_command("S3,90")
            
            if pan_success and tilt_success:
                self.current_pan = 90
                self.current_tilt = 90
                logger.info("Turret centered")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error centering turret: {e}")
            return False
    
    def get_position(self):
        """Get current turret position.
        
        Returns:
            tuple: (current_pan, current_tilt) in degrees
        """
        return (self.current_pan, self.current_tilt)
    
    def test_connection(self):
        """Test if Arduino is responding to commands.
        
        Sends a simple pan command and checks for response.
        
        Returns:
            bool: True if Arduino responds, False otherwise
        """
        if self.serial_connection is None:
            logger.error("Cannot test connection: Serial port not connected")
            return False
        
        try:
            logger.info("Testing Arduino connection...")
            
            # Clear any pending data
            self.serial_connection.reset_input_buffer()
            
            # Send a simple pan command
            test_command = "S2,90\n"
            self.serial_connection.write(test_command.encode('utf-8'))
            self.serial_connection.flush()
            
            # Wait for response
            time.sleep(0.2)
            
            # Check for ACK
            if self.serial_connection.in_waiting > 0:
                response = self.serial_connection.readline().decode('utf-8').strip()
                logger.info(f"Arduino responded: {response}")
                
                if "ACK" in response:
                    logger.info("✓ Arduino connection test PASSED")
                    return True
                else:
                    logger.warning(f"Unexpected response from Arduino: {response}")
                    return False
            else:
                logger.error("✗ No response from Arduino (check baud rate, port, and uploaded sketch)")
                return False
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def cleanup(self):
        """Close serial connection and cleanup resources."""
        try:
            logger.info("Cleaning up turret controller")
            
            # Center turret before shutdown
            self.center_turret()
            
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


# Example usage
if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create turret controller
    turret = TurretController(serial_port='COM11', baud_rate=9600)
    
    try:
        # Center turret
        turret.center_turret()
        time.sleep(1)
        
        # Simulate tracking a target
        # Target bbox at (320, 240, 50, 50) in 640x480 frame (centered)
        logger.info("Test 1: Centered target (should not move)")
        turret.track_target((320, 240, 50, 50), (480, 640, 3))
        time.sleep(1)
        
        # Target to the right (high X)
        logger.info("Test 2: Target to the right")
        turret.track_target((450, 240, 50, 50), (480, 640, 3))
        time.sleep(1)
        
        # Target to the left (low X)
        logger.info("Test 3: Target to the left")
        turret.track_target((100, 240, 50, 50), (480, 640, 3))
        time.sleep(1)
        
        # Target above (low Y)
        logger.info("Test 4: Target above center")
        turret.track_target((320, 100, 50, 50), (480, 640, 3))
        time.sleep(1)
        
        # Target below (high Y)
        logger.info("Test 5: Target below center")
        turret.track_target((320, 400, 50, 50), (480, 640, 3))
        time.sleep(1)
        
        # Re-center
        logger.info("Re-centering turret")
        turret.center_turret()
        time.sleep(1)
        
        logger.info(f"Current position: {turret.get_position()}")
        
    finally:
        turret.cleanup()
