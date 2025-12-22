#!/usr/bin/env python3
"""
Window Lock Bridge Service
===========================
Subscribes to theft/lockdown events and sends window lock commands to Arduino.

MQTT Topics:
- Subscribes: sentinel/alerts (for theft detection)
              sentinel/level2/events (for lockdown events)
- Publishes:  sentinel/arduino/commands

Trigger Conditions:
- Alert level "critical" with "theft" or "intruder" in message
- Lockdown events from Interior Watch

Commands Sent:
- Lock window: "S4,+2500" (CW half-cycle)
- Full lockdown: "LOCKDOWN" (locks door S1 and window S4)
"""

import os
import sys
import json
import time
import paho.mqtt.client as mqtt
from pathlib import Path

# Add parent directory for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class WindowLockBridge:
    """
    Bridge service that triggers window lock on theft/lockdown events.
    """
    
    # MQTT topics
    ALERTS_TOPIC = "sentinel/alerts"
    LEVEL2_EVENTS_TOPIC = "sentinel/level2/events"
    ARDUINO_COMMANDS_TOPIC = "sentinel/arduino/commands"
    
    # Window servo configuration
    WINDOW_SERVO = "S4"
    LOCK_DURATION_MS = 2500  # Half-cycle for continuous rotation servo
    
    # Rate limiting
    MIN_LOCKDOWN_INTERVAL_SECONDS = 10.0  # Prevent rapid lockdowns
    
    def __init__(self):
        """Initialize the window lock bridge."""
        # MQTT configuration
        self.mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        
        # State tracking
        self.mqtt_client = None
        self.running = True
        self.last_lockdown_time = 0
        self.window_locked = True  # Assume window starts locked
        
        print(f"[WINDOW_LOCK_BRIDGE] Initialized")
        print(f"[WINDOW_LOCK_BRIDGE] Window servo: {self.WINDOW_SERVO}")
        print(f"[WINDOW_LOCK_BRIDGE] Lock duration: {self.LOCK_DURATION_MS}ms")
    
    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection."""
        if reason_code == 0:
            print(f"[WINDOW_LOCK_BRIDGE] [OK] MQTT connected")
            # Subscribe to multiple topics
            client.subscribe(self.ALERTS_TOPIC)
            client.subscribe(self.LEVEL2_EVENTS_TOPIC)
            print(f"[WINDOW_LOCK_BRIDGE] Subscribed to: {self.ALERTS_TOPIC}")
            print(f"[WINDOW_LOCK_BRIDGE] Subscribed to: {self.LEVEL2_EVENTS_TOPIC}")
        else:
            print(f"[WINDOW_LOCK_BRIDGE] [ERROR] MQTT connection failed (rc={reason_code})")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming messages."""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # Try to parse as JSON
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                # If not JSON, treat as simple string
                data = {"message": payload}
            
            if topic == self.ALERTS_TOPIC:
                self._process_alert(data)
            elif topic == self.LEVEL2_EVENTS_TOPIC:
                self._process_level2_event(data)
                
        except Exception as e:
            print(f"[WINDOW_LOCK_BRIDGE] [ERROR] Error processing message: {e}")
    
    def _process_alert(self, data):
        """
        Process alert messages.
        
        Args:
            data: Alert data dictionary
        """
        level = data.get('level', '').lower()
        message = data.get('message', '').lower()
        
        # Check for theft/intruder related critical alerts
        is_critical = level == 'critical'
        is_theft_related = any(word in message for word in ['theft', 'intruder', 'stolen', 'lockdown'])
        
        if is_critical and is_theft_related:
            print(f"[WINDOW_LOCK_BRIDGE] [ALERT] Critical alert detected: {data.get('message', 'unknown')}")
            self._trigger_lockdown("critical_alert")
    
    def _process_level2_event(self, data):
        """
        Process Level 2 (Interior Watch) events.
        
        Args:
            data: Event data dictionary or string
        """
        # Handle string messages
        if isinstance(data, str):
            if 'lockdown' in data.lower() or 'theft' in data.lower():
                print(f"[WINDOW_LOCK_BRIDGE] [ALERT] Level 2 event: {data}")
                self._trigger_lockdown("level2_event")
            return
        
        # Handle dictionary messages
        event_type = data.get('type', data.get('event', '')).lower()
        
        if any(word in event_type for word in ['lockdown', 'theft', 'intruder', 'alert']):
            print(f"[WINDOW_LOCK_BRIDGE] [ALERT] Level 2 event detected: {event_type}")
            self._trigger_lockdown("level2_event")
    
    def _trigger_lockdown(self, reason):
        """
        Trigger lockdown - lock windows (and optionally full lockdown).
        
        Args:
            reason: Reason for lockdown
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_lockdown_time
        
        if time_since_last < self.MIN_LOCKDOWN_INTERVAL_SECONDS:
            remaining = self.MIN_LOCKDOWN_INTERVAL_SECONDS - time_since_last
            print(f"[WINDOW_LOCK_BRIDGE] Rate limited. Wait {remaining:.1f}s")
            return
        
        print(f"[WINDOW_LOCK_BRIDGE] >> TRIGGERING LOCKDOWN - Reason: {reason}")
        
        # Send full lockdown command (locks both door and window)
        self._send_arduino_command("LOCKDOWN")
        
        self.window_locked = True
        self.last_lockdown_time = current_time
    
    def _lock_window_only(self):
        """Lock just the window servo."""
        if self.window_locked:
            print(f"[WINDOW_LOCK_BRIDGE] Window already locked")
            return
        
        print(f"[WINDOW_LOCK_BRIDGE] >> Locking window only")
        
        # Send window lock command (CW rotation)
        cmd = f"{self.WINDOW_SERVO},+{self.LOCK_DURATION_MS}"
        self._send_arduino_command(cmd)
        
        self.window_locked = True
    
    def _send_arduino_command(self, command):
        """
        Send command to Arduino via MQTT.
        
        Args:
            command: Command string
        """
        if self.mqtt_client:
            self.mqtt_client.publish(self.ARDUINO_COMMANDS_TOPIC, command)
            print(f"[WINDOW_LOCK_BRIDGE] Sent: {command}")
    
    def connect_mqtt(self):
        """Connect to MQTT broker."""
        try:
            print(f"[WINDOW_LOCK_BRIDGE] Connecting to MQTT broker...")
            
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="window_lock_bridge")
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            return True
            
        except Exception as e:
            print(f"[WINDOW_LOCK_BRIDGE] [ERROR] MQTT connection failed: {e}")
            return False
    
    def run(self):
        """Main run loop."""
        print(f"[WINDOW_LOCK_BRIDGE] Starting Window Lock Bridge Service...")
        
        # Connect to MQTT
        while self.running and not self.connect_mqtt():
            print(f"[WINDOW_LOCK_BRIDGE] Retrying MQTT connection in 5s...")
            time.sleep(5)
        
        # Start MQTT loop
        self.mqtt_client.loop_start()
        
        print(f"[WINDOW_LOCK_BRIDGE] [OK] Service running. Monitoring for theft/lockdown events...")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[WINDOW_LOCK_BRIDGE] Shutdown requested...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the service."""
        print(f"[WINDOW_LOCK_BRIDGE] Shutting down...")
        self.running = False
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        print(f"[WINDOW_LOCK_BRIDGE] Shutdown complete")


def main():
    """Main entry point."""
    service = WindowLockBridge()
    service.run()


if __name__ == "__main__":
    main()
