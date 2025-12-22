#!/usr/bin/env python3
"""
Arduino Gateway Service
========================
MQTT-to-Serial bridge for centralized Arduino hardware control.

This service:
- Subscribes to MQTT topic: sentinel/arduino/commands
- Forwards commands to Arduino via serial
- Handles serial connection with auto-reconnect

Command Format (via MQTT payload):
- "S1,+2500"   - Move servo 1 clockwise for 2500ms
- "S2,-1500"   - Move servo 2 counter-clockwise for 1500ms
- "LOCKDOWN"   - Lock all doors/windows
- "UNLOCK"     - Unlock all doors/windows
- "FIRE"       - Activate shooter motors
- "STOP_ALL"   - Stop all servos and motors

Environment Variables:
- ARDUINO_PORT: Serial port (default: COM5)
- ARDUINO_BAUDRATE: Baud rate (default: 9600)
"""

import os
import sys
import time
import json
import serial
import threading
import paho.mqtt.client as mqtt
from pathlib import Path

# Add parent directory for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ArduinoGateway:
    """
    MQTT-to-Serial gateway for Arduino hardware control.
    
    Subscribes to sentinel/arduino/commands and forwards to Arduino.
    """
    
    MQTT_TOPIC = "sentinel/arduino/commands"
    RECONNECT_DELAY_SECONDS = 5
    
    def __init__(self):
        """Initialize the Arduino Gateway."""
        # Serial configuration from environment
        self.serial_port = os.getenv("ARDUINO_PORT", "COM5")
        self.baud_rate = int(os.getenv("ARDUINO_BAUDRATE", "9600"))
        
        # MQTT configuration
        self.mqtt_broker = os.getenv("MQTT_BROKER", "localhost")
        self.mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        
        # State
        self.serial_conn = None
        self.mqtt_client = None
        self.running = True
        self.serial_lock = threading.Lock()
        self.serial_reader_thread = None
        
        print(f"[ARDUINO_GATEWAY] Initialized")
        print(f"[ARDUINO_GATEWAY] Serial: {self.serial_port} @ {self.baud_rate}")
        print(f"[ARDUINO_GATEWAY] MQTT: {self.mqtt_broker}:{self.mqtt_port}")
    
    def _serial_reader(self):
        """
        Background thread to read and display Arduino responses.
        """
        while self.running:
            try:
                if self.serial_conn and self.serial_conn.is_open and self.serial_conn.in_waiting > 0:
                    with self.serial_lock:
                        line = self.serial_conn.readline().decode('utf-8', errors='replace').strip()
                        if line:
                            print(f"[ARDUINO_GATEWAY] RX << Arduino: {line}")
                else:
                    time.sleep(0.1)
            except Exception as e:
                if self.running:
                    print(f"[ARDUINO_GATEWAY] [ERROR] Serial read error: {e}")
                time.sleep(0.5)
    
    def connect_serial(self):
        """
        Connect to Arduino via serial port.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            if self.serial_conn and self.serial_conn.is_open:
                return True
            
            print(f"[ARDUINO_GATEWAY] Connecting to Arduino on {self.serial_port}...")
            
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1
            )
            
            # Wait for Arduino to reset after serial connection
            time.sleep(2)
            
            # Start serial reader thread
            if self.serial_reader_thread is None or not self.serial_reader_thread.is_alive():
                self.serial_reader_thread = threading.Thread(target=self._serial_reader, daemon=True)
                self.serial_reader_thread.start()
            
            print(f"[ARDUINO_GATEWAY] [OK] Arduino connected on {self.serial_port}")
            return True
            
        except serial.SerialException as e:
            print(f"[ARDUINO_GATEWAY] [ERROR] Serial connection failed: {e}")
            self.serial_conn = None
            return False
        except Exception as e:
            print(f"[ARDUINO_GATEWAY] [ERROR] Unexpected error: {e}")
            self.serial_conn = None
            return False
    
    def send_command(self, command):
        """
        Send a command to Arduino via serial.
        
        Args:
            command: String command to send (e.g., "S1,+2500", "FIRE")
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        with self.serial_lock:
            try:
                # Ensure connection
                if not self.serial_conn or not self.serial_conn.is_open:
                    if not self.connect_serial():
                        return False
                
                # Format command with newline terminator
                cmd_bytes = f"{command}\n".encode('utf-8')
                
                self.serial_conn.write(cmd_bytes)
                self.serial_conn.flush()
                
                print(f"[ARDUINO_GATEWAY] TX >> {command}")
                return True
                
            except serial.SerialException as e:
                print(f"[ARDUINO_GATEWAY] [ERROR] Serial write error: {e}")
                self.serial_conn = None
                return False
            except Exception as e:
                print(f"[ARDUINO_GATEWAY] [ERROR] Send error: {e}")
                return False
    
    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """
        Callback when MQTT client connects.
        
        Args:
            client: MQTT client instance
            userdata: User data
            flags: Connection flags
            reason_code: Reason code (0 = success)
            properties: MQTT v5 properties
        """
        if reason_code == 0:
            print(f"[ARDUINO_GATEWAY] [OK] MQTT connected")
            # Subscribe to commands topic
            client.subscribe(self.MQTT_TOPIC)
            print(f"[ARDUINO_GATEWAY] Subscribed to: {self.MQTT_TOPIC}")
        else:
            print(f"[ARDUINO_GATEWAY] [ERROR] MQTT connection failed (rc={reason_code})")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """
        Callback when MQTT message received.
        
        Args:
            client: MQTT client instance
            userdata: User data
            msg: MQTT message object
        """
        try:
            payload = msg.payload.decode('utf-8').strip()
            print(f"[ARDUINO_GATEWAY] RX << {msg.topic}: {payload}")
            
            # Forward command to Arduino
            self.send_command(payload)
            
        except Exception as e:
            print(f"[ARDUINO_GATEWAY] [ERROR] Message handling error: {e}")
    
    def _on_mqtt_disconnect(self, client, userdata, flags, reason_code, properties):
        """
        Callback when MQTT client disconnects.
        
        Args:
            client: MQTT client instance
            userdata: User data
            flags: Disconnect flags
            reason_code: Reason code
            properties: MQTT v5 properties
        """
        print(f"[ARDUINO_GATEWAY] MQTT disconnected (rc={reason_code})")
        if self.running:
            print(f"[ARDUINO_GATEWAY] Will attempt reconnect...")
    
    def connect_mqtt(self):
        """
        Connect to MQTT broker.
        
        Returns:
            bool: True if connected, False otherwise
        """
        try:
            print(f"[ARDUINO_GATEWAY] Connecting to MQTT broker...")
            
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="arduino_gateway")
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_message = self._on_mqtt_message
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, keepalive=60)
            
            return True
            
        except Exception as e:
            print(f"[ARDUINO_GATEWAY] [ERROR] MQTT connection failed: {e}")
            return False
    
    def run(self):
        """
        Main run loop for the gateway service.
        
        Connects to Arduino and MQTT, then processes messages.
        """
        print(f"[ARDUINO_GATEWAY] Starting Arduino Gateway Service...")
        
        # Initial Arduino connection (non-blocking if fails)
        self.connect_serial()
        
        # Connect to MQTT
        if not self.connect_mqtt():
            print(f"[ARDUINO_GATEWAY] [ERROR] Failed to connect to MQTT. Retrying...")
            while self.running and not self.connect_mqtt():
                time.sleep(self.RECONNECT_DELAY_SECONDS)
        
        # Start MQTT loop
        self.mqtt_client.loop_start()
        
        print(f"[ARDUINO_GATEWAY] [OK] Gateway running. Waiting for commands...")
        
        # Keep alive and monitor connections
        try:
            while self.running:
                # Periodically check serial connection
                if not self.serial_conn or not self.serial_conn.is_open:
                    self.connect_serial()
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            print(f"\n[ARDUINO_GATEWAY] Shutdown requested...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Gracefully shutdown the gateway."""
        print(f"[ARDUINO_GATEWAY] Shutting down...")
        self.running = False
        
        # Stop MQTT
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        # Close serial
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        
        print(f"[ARDUINO_GATEWAY] Shutdown complete")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Arduino Gateway Service')
    parser.add_argument('--test', action='store_true', help='Run servo test on startup')
    args = parser.parse_args()
    
    gateway = ArduinoGateway()
    
    if args.test:
        # Test mode: send test commands directly
        print(f"[ARDUINO_GATEWAY] === TEST MODE ===")
        if gateway.connect_serial():
            import time
            test_commands = [
                ("S2,+500", "Pan servo CW 500ms"),
                ("S2,-500", "Pan servo CCW 500ms"),
                ("S3,+500", "Tilt servo CW 500ms"),
                ("S3,-500", "Tilt servo CCW 500ms"),
            ]
            for cmd, desc in test_commands:
                print(f"[ARDUINO_GATEWAY] Testing: {desc}")
                gateway.send_command(cmd)
                time.sleep(1.5)  # Wait for movement + settle time
            print(f"[ARDUINO_GATEWAY] === TEST COMPLETE ===")
        else:
            print(f"[ARDUINO_GATEWAY] [ERROR] Could not connect to Arduino for test")
    
    gateway.run()


if __name__ == "__main__":
    main()
