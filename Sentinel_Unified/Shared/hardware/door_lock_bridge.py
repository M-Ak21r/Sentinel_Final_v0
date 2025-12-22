#!/usr/bin/env python3
"""
Door Lock Bridge Service
=========================
Subscribes to door control events and sends lock/unlock commands to Arduino.

MQTT Topics:
- Subscribes: sentinel/door/control
- Publishes:  sentinel/arduino/commands

Expected Message Format (JSON):
{
    "action": "unlock" | "lock",
    "user": "optional_username",
    "reason": "optional_reason"
}

Commands Sent:
- Lock:   "S1,+2500" (CW half-cycle)
- Unlock: "S1,-2500" (CCW half-cycle)
"""

import os
import sys
import json
import time
import threading
import paho.mqtt.client as mqtt
from pathlib import Path

# Add parent directory for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class DoorLockBridge:
    """
    Bridge service that translates door control MQTT events to Arduino commands.
    """
    
    # MQTT topics
    DOOR_CONTROL_TOPIC = "sentinel/door/control"
    ARDUINO_COMMANDS_TOPIC = "sentinel/arduino/commands"
    
    # Door servo configuration
    DOOR_SERVO = "S1"
    LOCK_DURATION_MS = 2500  # Half-cycle for continuous rotation servo
    AUTO_LOCK_DELAY_SECONDS = 5.0  # Auto-lock after this many seconds
    
    # Rate limiting
    MIN_OPERATION_INTERVAL_SECONDS = 3.0
    
    def __init__(self):
        """Initialize the door lock bridge."""
        # MQTT configuration
        self.mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        
        # State tracking
        self.mqtt_client = None
        self.running = True
        self.last_operation_time = 0
        self.door_locked = True  # Assume door starts locked
        self.auto_lock_timer = None  # Timer for auto-lock
        
        print(f"[DOOR_LOCK_BRIDGE] Initialized")
        print(f"[DOOR_LOCK_BRIDGE] Door servo: {self.DOOR_SERVO}")
        print(f"[DOOR_LOCK_BRIDGE] Lock duration: {self.LOCK_DURATION_MS}ms")
    
    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection."""
        if reason_code == 0:
            print(f"[DOOR_LOCK_BRIDGE] [OK] MQTT connected")
            client.subscribe(self.DOOR_CONTROL_TOPIC)
            print(f"[DOOR_LOCK_BRIDGE] Subscribed to: {self.DOOR_CONTROL_TOPIC}")
        else:
            print(f"[DOOR_LOCK_BRIDGE] [ERROR] MQTT connection failed (rc={reason_code})")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming door control messages."""
        try:
            print(f"[DOOR_LOCK_BRIDGE] Received message on {msg.topic}: {msg.payload.decode('utf-8')}")
            data = json.loads(msg.payload.decode('utf-8'))
            self._process_door_command(data)
        except json.JSONDecodeError as e:
            print(f"[DOOR_LOCK_BRIDGE] [ERROR] Invalid JSON: {e}")
        except Exception as e:
            print(f"[DOOR_LOCK_BRIDGE] [ERROR] Error processing message: {e}")
    
    def _process_door_command(self, data):
        """
        Process door control command.
        
        Args:
            data: Dictionary with 'action' and optional 'user', 'reason'
        """
        action = data.get('action', '').lower()
        user = data.get('user', 'unknown')
        reason = data.get('reason', '')
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_operation_time
        
        if time_since_last < self.MIN_OPERATION_INTERVAL_SECONDS:
            remaining = self.MIN_OPERATION_INTERVAL_SECONDS - time_since_last
            print(f"[DOOR_LOCK_BRIDGE] Rate limited. Wait {remaining:.1f}s")
            return
        
        if action == 'unlock':
            self._unlock_door(user, reason)
        elif action == 'lock':
            self._lock_door(user, reason)
        else:
            print(f"[DOOR_LOCK_BRIDGE] Unknown action: {action}")
    
    def _unlock_door(self, user, reason):
        """
        Unlock the door.
        
        Args:
            user: Username requesting unlock
            reason: Reason for unlock
        """
        print(f"[DOOR_LOCK_BRIDGE] >> UNLOCKING door for {user}")
        if reason:
            print(f"[DOOR_LOCK_BRIDGE] Reason: {reason}")
        
        # Send unlock command (CCW rotation)
        cmd = f"{self.DOOR_SERVO},-{self.LOCK_DURATION_MS}"
        self._send_arduino_command(cmd)
        
        self.door_locked = False
        self.last_operation_time = time.time()
        
        # Schedule auto-lock after delay
        self._schedule_auto_lock()
    
    def _lock_door(self, user, reason):
        """
        Lock the door.
        
        Args:
            user: Username requesting lock
            reason: Reason for lock
        """
        if self.door_locked:
            print(f"[DOOR_LOCK_BRIDGE] Door already locked")
            return
        
        print(f"[DOOR_LOCK_BRIDGE] >> LOCKING door by {user}")
        if reason:
            print(f"[DOOR_LOCK_BRIDGE] Reason: {reason}")
        
        # Send lock command (CW rotation)
        cmd = f"{self.DOOR_SERVO},+{self.LOCK_DURATION_MS}"
        self._send_arduino_command(cmd)
        
        self.door_locked = True
        self.last_operation_time = time.time()
        
        # Cancel any pending auto-lock timer
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
            self.auto_lock_timer = None
    
    def _schedule_auto_lock(self):
        """Schedule automatic re-lock after delay."""
        # Cancel any existing timer
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
        
        print(f"[DOOR_LOCK_BRIDGE] Auto-lock scheduled in {self.AUTO_LOCK_DELAY_SECONDS}s")
        
        self.auto_lock_timer = threading.Timer(
            self.AUTO_LOCK_DELAY_SECONDS,
            self._auto_lock_callback
        )
        self.auto_lock_timer.daemon = True  # Ensure timer doesn't block shutdown
        self.auto_lock_timer.start()
    
    def _auto_lock_callback(self):
        """Callback for auto-lock timer."""
        print(f"[DOOR_LOCK_BRIDGE] Auto-lock timer fired! door_locked={self.door_locked}, running={self.running}")
        if not self.door_locked and self.running:
            print(f"[DOOR_LOCK_BRIDGE] >> AUTO-LOCKING door (timer expired)")
            
            # Send lock command (CW rotation)
            cmd = f"{self.DOOR_SERVO},+{self.LOCK_DURATION_MS}"
            self._send_arduino_command(cmd)
            
            self.door_locked = True
            self.last_operation_time = time.time()
        
        self.auto_lock_timer = None
    
    def _send_arduino_command(self, command):
        """
        Send command to Arduino via MQTT.
        
        Args:
            command: Command string
        """
        if self.mqtt_client:
            self.mqtt_client.publish(self.ARDUINO_COMMANDS_TOPIC, command)
            print(f"[DOOR_LOCK_BRIDGE] Sent: {command}")
    
    def connect_mqtt(self):
        """Connect to MQTT broker."""
        try:
            print(f"[DOOR_LOCK_BRIDGE] Connecting to MQTT broker...")
            
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="door_lock_bridge")
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            return True
            
        except Exception as e:
            print(f"[DOOR_LOCK_BRIDGE] [ERROR] MQTT connection failed: {e}")
            return False
    
    def run(self):
        """Main run loop."""
        print(f"[DOOR_LOCK_BRIDGE] Starting Door Lock Bridge Service...")
        
        # Connect to MQTT
        while self.running and not self.connect_mqtt():
            print(f"[DOOR_LOCK_BRIDGE] Retrying MQTT connection in 5s...")
            time.sleep(5)
        
        # Start MQTT loop
        self.mqtt_client.loop_start()
        
        print(f"[DOOR_LOCK_BRIDGE] [OK] Service running. Waiting for door control commands...")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[DOOR_LOCK_BRIDGE] Shutdown requested...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the service."""
        print(f"[DOOR_LOCK_BRIDGE] Shutting down...")
        self.running = False
        
        # Cancel auto-lock timer
        if self.auto_lock_timer:
            self.auto_lock_timer.cancel()
            self.auto_lock_timer = None
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        print(f"[DOOR_LOCK_BRIDGE] Shutdown complete")


def main():
    """Main entry point."""
    service = DoorLockBridge()
    service.run()


if __name__ == "__main__":
    main()
