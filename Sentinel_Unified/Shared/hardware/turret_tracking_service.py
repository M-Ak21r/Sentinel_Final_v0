#!/usr/bin/env python3
"""
Turret Tracking Service
========================
Subscribes to face tracking data and controls pan/tilt servos to track faces.
Automatically fires when face is centered for 5+ consecutive frames.

MQTT Topics:
- Subscribes: sentinel/door/face_tracking
- Publishes:  sentinel/arduino/commands

Auto-Fire Logic:
- Center zone: ±20 pixels from frame center
- Fire after: 5 consecutive centered frames
- Cooldown: 3 seconds between shots

Servo Mapping:
- S2 (Pin 9):  Pan servo (horizontal tracking)
- S3 (Pin 11): Tilt servo (vertical tracking)
"""

import os
import sys
import json
import time
import paho.mqtt.client as mqtt
from pathlib import Path

# Add parent directory for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TurretTrackingService:
    """
    Service that tracks faces with pan/tilt servos and auto-fires.
    """
    
    # MQTT topics
    FACE_TRACKING_TOPIC = "sentinel/door/face_tracking"
    ARDUINO_COMMANDS_TOPIC = "sentinel/arduino/commands"
    
    # Tracking configuration
    CENTER_THRESHOLD_PX = 20      # Pixels from center to consider "centered"
    FRAMES_TO_FIRE = 5            # Consecutive centered frames before firing
    FIRE_COOLDOWN_SECONDS = 3.0   # Minimum time between shots
    
    # Servo movement configuration
    PAN_MOVE_DURATION_MS = 300    # Duration for pan adjustment (increased for visible movement)
    TILT_MOVE_DURATION_MS = 300   # Duration for tilt adjustment (increased for visible movement)
    DEAD_ZONE_PX = 10             # Don't move if within dead zone
    
    def __init__(self):
        """Initialize the turret tracking service."""
        # MQTT configuration
        self.mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        
        # State tracking
        self.mqtt_client = None
        self.running = True
        self.centered_frames = 0
        self.last_fire_time = 0
        
        print(f"[TURRET_TRACKING] Initialized")
        print(f"[TURRET_TRACKING] Center threshold: +/-{self.CENTER_THRESHOLD_PX}px")
        print(f"[TURRET_TRACKING] Frames to fire: {self.FRAMES_TO_FIRE}")
        print(f"[TURRET_TRACKING] Fire cooldown: {self.FIRE_COOLDOWN_SECONDS}s")
    
    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection."""
        if reason_code == 0:
            print(f"[TURRET_TRACKING] [OK] MQTT connected")
            client.subscribe(self.FACE_TRACKING_TOPIC)
            print(f"[TURRET_TRACKING] Subscribed to: {self.FACE_TRACKING_TOPIC}")
        else:
            print(f"[TURRET_TRACKING] [ERROR] MQTT connection failed (rc={reason_code})")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming face tracking messages."""
        try:
            data = json.loads(msg.payload.decode('utf-8'))
            self._process_tracking_data(data)
        except json.JSONDecodeError as e:
            print(f"[TURRET_TRACKING] [ERROR] Invalid JSON: {e}")
        except Exception as e:
            print(f"[TURRET_TRACKING] [ERROR] Error processing message: {e}")
    
    def _process_tracking_data(self, data):
        """
        Process face tracking data and control turret.
        
        Args:
            data: Dictionary with 'faces' and 'frame_size'
        """
        faces = data.get('faces', [])
        frame_size = data.get('frame_size', [640, 480])
        
        if not faces:
            # No faces - reset centered counter
            self.centered_frames = 0
            return
        
        # Track the first (primary) face
        face = faces[0]
        bbox = face.get('bbox', [0, 0, 0, 0])
        x1, y1, x2, y2 = bbox
        
        # Calculate face center
        face_center_x = (x1 + x2) // 2
        face_center_y = (y1 + y2) // 2
        
        # Calculate frame center
        frame_w, frame_h = frame_size
        frame_center_x = frame_w // 2
        frame_center_y = frame_h // 2
        
        # Calculate offset from center
        offset_x = face_center_x - frame_center_x  # Positive = face is right of center
        offset_y = face_center_y - frame_center_y  # Positive = face is below center
        
        # Check if centered
        is_centered_x = abs(offset_x) <= self.CENTER_THRESHOLD_PX
        is_centered_y = abs(offset_y) <= self.CENTER_THRESHOLD_PX
        is_centered = is_centered_x and is_centered_y
        
        if is_centered:
            self.centered_frames += 1
            print(f"[TURRET_TRACKING] Face CENTERED ({self.centered_frames}/{self.FRAMES_TO_FIRE})")
            
            # Check if should fire
            if self.centered_frames >= self.FRAMES_TO_FIRE:
                self._try_fire()
        else:
            self.centered_frames = 0
            
            # Move servos to track face
            self._adjust_pan_tilt(offset_x, offset_y)
    
    def _adjust_pan_tilt(self, offset_x, offset_y):
        """
        Adjust pan/tilt servos based on offset.
        
        Args:
            offset_x: Horizontal offset (positive = move right)
            offset_y: Vertical offset (positive = move down)
        """
        # Skip if within dead zone (to avoid jitter)
        if abs(offset_x) <= self.DEAD_ZONE_PX and abs(offset_y) <= self.DEAD_ZONE_PX:
            return
        
        print(f"[TURRET_TRACKING] Adjusting - offset_x={offset_x}, offset_y={offset_y}")
        
        # Pan (horizontal) - S2
        if abs(offset_x) > self.DEAD_ZONE_PX:
            # Direction: positive offset = face is right = pan right (CW)
            direction = "+" if offset_x > 0 else "-"
            cmd = f"S2,{direction}{self.PAN_MOVE_DURATION_MS}"
            print(f"[TURRET_TRACKING] PAN command: {cmd}")
            self._send_arduino_command(cmd)
        
        # Tilt (vertical) - S3
        if abs(offset_y) > self.DEAD_ZONE_PX:
            # Direction: positive offset = face is below = tilt down (CW)
            direction = "+" if offset_y > 0 else "-"
            cmd = f"S3,{direction}{self.TILT_MOVE_DURATION_MS}"
            print(f"[TURRET_TRACKING] TILT command: {cmd}")
            self._send_arduino_command(cmd)
    
    def _try_fire(self):
        """Attempt to fire if cooldown has elapsed."""
        current_time = time.time()
        time_since_last_fire = current_time - self.last_fire_time
        
        if time_since_last_fire >= self.FIRE_COOLDOWN_SECONDS:
            print(f"[TURRET_TRACKING] >>> FIRING! <<<")
            self._send_arduino_command("FIRE")
            self.last_fire_time = current_time
            self.centered_frames = 0  # Reset after firing
        else:
            remaining = self.FIRE_COOLDOWN_SECONDS - time_since_last_fire
            print(f"[TURRET_TRACKING] Cooldown: {remaining:.1f}s remaining")
    
    def _send_arduino_command(self, command):
        """
        Send command to Arduino via MQTT.
        
        Args:
            command: Command string (e.g., "S2,+100", "FIRE")
        """
        if self.mqtt_client and self.mqtt_client.is_connected():
            result = self.mqtt_client.publish(self.ARDUINO_COMMANDS_TOPIC, command)
            if result.rc == 0:
                print(f"[TURRET_TRACKING] >> SENT: {command}")
            else:
                print(f"[TURRET_TRACKING] [ERROR] Failed to publish: {command} (rc={result.rc})")
        else:
            print(f"[TURRET_TRACKING] [ERROR] MQTT not connected, cannot send: {command}")
    
    def connect_mqtt(self):
        """Connect to MQTT broker."""
        try:
            print(f"[TURRET_TRACKING] Connecting to MQTT broker...")
            
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="turret_tracking_service")
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            return True
            
        except Exception as e:
            print(f"[TURRET_TRACKING] [ERROR] MQTT connection failed: {e}")
            return False
    
    def run(self):
        """Main run loop."""
        print(f"[TURRET_TRACKING] Starting Turret Tracking Service...")
        
        # Connect to MQTT
        while self.running and not self.connect_mqtt():
            print(f"[TURRET_TRACKING] Retrying MQTT connection in 5s...")
            time.sleep(5)
        
        # Start MQTT loop
        self.mqtt_client.loop_start()
        
        print(f"[TURRET_TRACKING] [OK] Service running. Waiting for face tracking data...")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[TURRET_TRACKING] Shutdown requested...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the service."""
        print(f"[TURRET_TRACKING] Shutting down...")
        self.running = False
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        print(f"[TURRET_TRACKING] Shutdown complete")


def main():
    """Main entry point."""
    service = TurretTrackingService()
    service.run()


if __name__ == "__main__":
    main()
