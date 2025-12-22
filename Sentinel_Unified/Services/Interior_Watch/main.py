"""
Interior Watch Microservice
============================
This service monitors the interior room and handles:
- Theft Detection: Track assets (laptops/phones) using YOLO11n
- Identity Check: Verify suspects using InsightFace (ArcFace)
- Active Defense: Automated turret tracking and engagement
- Evidence API: Provide REST API for browsing recorded theft videos

Author: Sentinel System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import logging
from dotenv import load_dotenv

# Import the theft detection system with turret support
from theft_detection import TheftDetectionSystem, app

# Load environment variables from root .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
load_dotenv(env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global system instance
theft_detection_system = None


def main():
    """Main entry point for Interior Watch microservice."""
    global theft_detection_system
    
    logger.info("=" * 60)
    logger.info("Interior Watch Microservice Starting")
    logger.info("With Active Defense Turret System")
    logger.info("=" * 60)
    
    try:
        # Load configuration from environment
        mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        camera_index = int(os.getenv('INTERIOR_CAMERA_INDEX', 1))
        arduino_port = os.getenv('ARDUINO_PORT', None)  # None = disabled
        arduino_baudrate = int(os.getenv('ARDUINO_BAUDRATE', 9600))
        port = int(os.getenv('INTERIOR_WATCH_PORT', 5002))
        
        # Initialize Theft Detection System with turret support
        logger.info("Initializing Theft Detection System...")
        theft_detection_system = TheftDetectionSystem(
            model_path="yolo11n.pt",
            authorized_dir="./authorized_personnel",
            camera_source=camera_index,
            arduino_port=arduino_port,
            arduino_baudrate=arduino_baudrate,
            mqtt_broker=mqtt_broker,
            mqtt_port=mqtt_port
        )
        
        logger.info(f"Starting Flask server on port {port}...")
        logger.info(f"Video feed available at: http://localhost:{port}/video_feed")
        logger.info(f"Health check available at: http://localhost:{port}/health")
        
        if arduino_port:
            logger.info(f"Active Defense System: ENABLED (Port: {arduino_port})")
        else:
            logger.warning("Active Defense System: DISABLED (No Arduino port specified)")
            logger.warning("Set ARDUINO_PORT environment variable to enable turret")
        
        logger.info("=" * 60)
        
        # Run Flask app
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("\nShutting down due to keyboard interrupt...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
    finally:
        if theft_detection_system is not None:
            logger.info("Cleaning up theft detection system...")
            theft_detection_system.cleanup()
        logger.info("Interior Watch service terminated")


if __name__ == "__main__":
    main()
