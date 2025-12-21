"""
Notification Gateway Microservice
==================================
This service monitors MQTT security events and dispatches SMS alerts via Twilio.
Normalizes alert signals from different services (Door_Sentry, Interior_Watch).

Author: Sentinel System
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import paho.mqtt.client as mqtt


# Load environment variables from root .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
load_dotenv(env_path)


# Configure logging to stdout with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class NotificationGateway:
    """
    Notification Gateway service for dispatching SMS alerts.
    
    This service consumes MQTT security events and normalizes alert levels
    from different services (Door_Sentry uses string levels, Interior_Watch uses numeric).
    """
    
    def __init__(self):
        """Initialize Notification Gateway with MQTT client."""
        logger.info("Initializing Notification Gateway...")
        
        # Load configuration from environment
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        
        # TODO: Phase 2 - SMS configuration for Twilio integration
        self.sms_provider_sid = os.getenv('SMS_PROVIDER_SID', '')
        self.sms_provider_token = os.getenv('SMS_PROVIDER_TOKEN', '')
        self.sms_from_number = os.getenv('SMS_FROM_NUMBER', '')
        self.alert_target_phone = os.getenv('ALERT_TARGET_PHONE', '')
        
        # Initialize state
        self.running = False
        
        # Initialize MQTT client
        logger.info(f"Setting up MQTT client (broker: {self.mqtt_broker}:{self.mqtt_port})...")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="notification_gateway")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info("MQTT client connected and loop started")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
        
        logger.info("Notification Gateway initialized successfully")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT client connects to broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            # Subscribe to alerts topic
            client.subscribe("sentinel/alerts")
            logger.info("Subscribed to sentinel/alerts")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg, properties=None):
        """
        Callback when MQTT message is received.
        Handles alert normalization from different service schemas.
        """
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            logger.debug(f"Received MQTT message on {msg.topic} - Size: {len(msg.payload)} bytes")
            
            # Normalize and process the alert
            self._process_alert(payload)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode MQTT message: {msg.payload} - Error: {e}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _process_alert(self, payload):
        """
        Process and normalize alert from different service schemas.
        
        Signal Normalization:
        - Case A (Door_Sentry): {"level": "critical", "msg": "...", ...}
        - Case B (Interior_Watch): {"level": 1, "type": "THEFT", "msg": "...", ...}
        
        Args:
            payload (dict): MQTT message payload
        """
        try:
            level = payload.get('level')
            message = payload.get('msg', 'No message')
            timestamp = payload.get('timestamp', datetime.now().isoformat())
            alert_type = payload.get('type', 'SECURITY_ALERT')
            source = payload.get('source', 'unknown')
            
            # Normalize alert level to determine priority
            is_high_priority = False
            
            # Case A: Door_Sentry uses string levels
            if isinstance(level, str):
                if level.lower() == 'critical':
                    is_high_priority = True
                    logger.debug(f"Door Sentry alert - level: {level} (string) -> HIGH PRIORITY")
            
            # Case B: Interior_Watch uses numeric levels
            elif isinstance(level, int):
                # 1=Critical, 2=Warning are HIGH PRIORITY
                # 3=Info is LOW PRIORITY
                if level in [1, 2]:
                    is_high_priority = True
                    logger.debug(f"Interior Watch alert - level: {level} (numeric) -> HIGH PRIORITY")
                else:
                    logger.debug(f"Interior Watch alert - level: {level} (numeric) -> LOW PRIORITY (Info)")
            else:
                # Unknown level type - log as info only (sanitized)
                logger.info(f"Alert with unknown level type: {type(level).__name__}")
                return
            
            # Process based on priority
            if is_high_priority:
                logger.info(f"[ALERT TRIGGERED] {alert_type}: {message}")
                # TODO: Phase 2 - Send SMS via Twilio API using self.sms_* configurations
                # For now, just log the high-priority alert
            else:
                logger.debug(f"Low priority alert: {alert_type} - {message}")
                
        except Exception as e:
            logger.error(f"Error in _process_alert: {e}")
    
    def run(self):
        """Run the notification gateway service."""
        self.running = True
        logger.info("Notification Gateway is now running...")
        logger.info(f"Listening for alerts on topic: sentinel/alerts")
        logger.info("Press Ctrl+C to stop")
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down due to keyboard interrupt...")
            self.running = False
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Notification Gateway...")
        self.running = False
        
        if self.mqtt_client is not None:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
        
        logger.info("Notification Gateway cleanup complete")


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Notification Gateway Microservice Starting")
    logger.info("=" * 60)
    
    gateway = None
    
    try:
        # Initialize Notification Gateway
        gateway = NotificationGateway()
        
        # Run the service
        gateway.run()
        
    except KeyboardInterrupt:
        logger.info("\nShutting down due to keyboard interrupt...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if gateway is not None:
            gateway.cleanup()


if __name__ == "__main__":
    main()
