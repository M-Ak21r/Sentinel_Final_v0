"""
Door Sentry Microservice
=========================
This service monitors the front door and handles:
- Video streaming to Web Interface
- Face authentication using FaceAuthenticator
- MQTT commands for door unlock and alerts
- Remote control via MQTT commands

Author: Sentinel System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import cv2
import json
import time
import logging
from datetime import datetime
from flask import Flask, Response
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

from Sentinel_Unified.Shared.libs.face_auth import FaceAuthenticator


# Load environment variables from root .env file
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
load_dotenv(env_path)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DoorSentry:
    """
    Door Sentry microservice for monitoring the front door.
    
    This class manages:
    - Camera video capture
    - Face authentication
    - MQTT communication for door control and alerts
    - Video streaming
    """
    
    # Configuration constants
    UNLOCK_RATE_LIMIT_SECONDS = 15
    INTRUDER_ALERT_THRESHOLD_SECONDS = 5
    
    def __init__(self):
        """Initialize Door Sentry with camera, face auth, and MQTT."""
        logger.info("Initializing Door Sentry...")
        
        # Load configuration from environment
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        self.camera_index = int(os.getenv('CAMERA_INDEX', 0))
        
        # Initialize state variables
        self.last_unlock_time = 0
        self.unknown_face_start_time = None
        self.running = False
        self.frame_count = 0
        self.process_every_n_frames = 3  # Process detection every 3rd frame for better FPS
        self.last_faces = []  # Cache last detection results
        
        # Initialize FaceAuthenticator
        logger.info("Initializing FaceAuthenticator...")
        try:
            self.auth = FaceAuthenticator(
                similarity_threshold=0.5,
                min_face_size=(30, 30)
            )
            logger.info(f"FaceAuthenticator initialized with {len(self.auth.get_known_faces())} known faces")
        except Exception as e:
            logger.error(f"Failed to initialize FaceAuthenticator: {e}")
            raise
        
        # Initialize camera
        logger.info(f"Opening camera (index: {self.camera_index})...")
        self.camera = cv2.VideoCapture(self.camera_index)
        if not self.camera.isOpened():
            logger.error("Failed to open camera")
            raise RuntimeError("Failed to open camera")
        
        # Set camera properties for better performance
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        logger.info("Camera opened successfully")
        
        # Initialize MQTT client
        logger.info(f"Setting up MQTT client (broker: {self.mqtt_broker}:{self.mqtt_port})...")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="door_sentry")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info("MQTT client connected and loop started")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            logger.warning("Continuing without MQTT - alerts and commands will not work")
        
        logger.info("Door Sentry initialized successfully")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT client connects to broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            # Subscribe to commands topic
            client.subscribe("sentinel/commands")
            logger.info("Subscribed to sentinel/commands")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg, properties=None):
        """Callback when MQTT message is received."""
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            logger.info(f"Received MQTT message on {msg.topic}: {payload}")
            self.mqtt_callback(payload)
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode MQTT message: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def mqtt_callback(self, msg):
        """
        Handle incoming MQTT commands.
        
        Args:
            msg (dict): MQTT message payload as dictionary
        """
        try:
            # Check if this command is for the door
            if msg.get('target') == 'door' and msg.get('command') == 'UNLOCK':
                logger.info("Received manual UNLOCK command via MQTT")
                self._publish_unlock(user="Manual Override")
            
            # Check if this command is for all services (hot-reload faces)
            elif msg.get('target') == 'all' and msg.get('action') == 'RELOAD_FACES':
                print(f"[{self.__class__.__name__}] Command received: Reloading faces...")
                logger.info("[System] Hot-reloading face database...")
                self.auth.reload_faces()
                logger.info(f"[System] Face database reloaded: {len(self.auth.get_known_faces())} faces")
        except Exception as e:
            logger.error(f"Error in mqtt_callback: {e}")
    
    def _is_mqtt_connected(self):
        """
        Check if MQTT client is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.mqtt_client is not None and self.mqtt_client.is_connected()
    
    def _publish_unlock(self, user="Unknown"):
        """
        Publish MQTT unlock command.
        
        Args:
            user (str): Name of the authorized user
        """
        if not self._is_mqtt_connected():
            logger.warning("MQTT client not connected, cannot publish unlock command")
            return
            
        try:
            payload = {
                "action": "UNLOCK",
                "user": user,
                "timestamp": datetime.now().isoformat()
            }
            result = self.mqtt_client.publish(
                "sentinel/door/control",
                json.dumps(payload),
                qos=1
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published UNLOCK command for user: {user}")
            else:
                logger.warning(f"Failed to publish UNLOCK command: {result.rc}")
        except Exception as e:
            logger.error(f"Error publishing unlock command: {e}")
    
    def _publish_alert(self, level="critical", message="Unknown"):
        """
        Publish MQTT alert.
        
        Args:
            level (str): Alert level (critical, warning, info)
            message (str): Alert message
        """
        if not self._is_mqtt_connected():
            logger.warning("MQTT client not connected, cannot publish alert")
            return
            
        try:
            payload = {
                "level": level,
                "msg": message,
                "timestamp": datetime.now().isoformat()
            }
            result = self.mqtt_client.publish(
                "sentinel/alerts",
                json.dumps(payload),
                qos=1
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published alert: {level} - {message}")
            else:
                logger.warning(f"Failed to publish alert: {result.rc}")
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
    
    def process_frame(self):
        """
        Process a single frame from the camera.
        
        Returns:
            bytes: Annotated frame as JPEG bytes, or None if error
        """
        # Read frame from camera
        ret, frame = self.camera.read()
        if not ret or frame is None:
            logger.warning("Failed to read frame from camera")
            return None
        
        self.frame_count += 1
        
        # Create a copy for annotation
        annotated_frame = frame.copy()
        current_time = time.time()
        
        # Perform face identification only every Nth frame for performance
        faces = []
        if self.frame_count % self.process_every_n_frames == 0:
            try:
                faces = self.auth.identify_face(frame)
                self.last_faces = faces  # Cache results
            except Exception as e:
                logger.error(f"Face identification error: {e}")
                faces = []
        else:
            # Use cached results from last detection
            faces = self.last_faces
        
        # Process detected faces
        try:
            if faces:
                has_unknown = False
                
                for face in faces:
                    name = face['name']
                    confidence = face['confidence']
                    bbox = face['bbox']
                    is_authorized = face['is_authorized']
                    
                    x1, y1, x2, y2 = bbox
                    
                    if is_authorized:
                        # Draw GREEN box for authorized face
                        color = (0, 255, 0)  # Green
                        label = f"{name} ({confidence:.2f})"
                        
                        # Check rate limit for unlock
                        if current_time - self.last_unlock_time > self.UNLOCK_RATE_LIMIT_SECONDS:
                            self._publish_unlock(user=name)
                            self.last_unlock_time = current_time
                        
                        # Reset unknown face timer
                        self.unknown_face_start_time = None
                        
                    else:
                        # Draw RED box for unknown face
                        color = (0, 0, 255)  # Red
                        label = "UNKNOWN"
                        has_unknown = True
                        
                        # Track unknown face duration
                        if self.unknown_face_start_time is None:
                            self.unknown_face_start_time = current_time
                        else:
                            duration = current_time - self.unknown_face_start_time
                            if duration > self.INTRUDER_ALERT_THRESHOLD_SECONDS:
                                self._publish_alert(
                                    level="critical",
                                    message="Intruder at door"
                                )
                                # Reset timer to avoid spam (re-alert every 5 seconds)
                                self.unknown_face_start_time = current_time
                    
                    # Draw bounding box
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw label background
                    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(
                        annotated_frame,
                        (x1, y1 - label_size[1] - 10),
                        (x1 + label_size[0], y1),
                        color,
                        -1
                    )
                    
                    # Draw label text
                    cv2.putText(
                        annotated_frame,
                        label,
                        (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )
                
                # Reset unknown timer if no unknown faces detected
                if not has_unknown:
                    self.unknown_face_start_time = None
            else:
                # No faces detected, reset unknown timer
                self.unknown_face_start_time = None
                
        except Exception as e:
            logger.error(f"Error during face identification: {e}")
        
        # Add timestamp to frame
        timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            annotated_frame,
            timestamp_text,
            (10, annotated_frame.shape[0] - 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
        
        # Add FPS counter for monitoring performance
        fps_text = f"Frame: {self.frame_count} (Processing every {self.process_every_n_frames})"
        cv2.putText(
            annotated_frame,
            fps_text,
            (10, annotated_frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1
        )
        
        # Encode frame to JPEG with optimized quality (70% instead of default 95%)
        ret, jpeg = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            logger.warning("Failed to encode frame as JPEG")
            return None
        
        return jpeg.tobytes()
    
    def generate_frames(self):
        """
        Generator function for Flask video streaming.
        
        Yields:
            bytes: Frame data in multipart format
        """
        self.running = True
        while self.running:
            frame_bytes = self.process_frame()
            
            if frame_bytes is not None:
                # Yield frame in multipart format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                # Small delay if frame processing failed
                time.sleep(0.1)
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Door Sentry...")
        self.running = False
        
        if self.camera is not None:
            self.camera.release()
            logger.info("Camera released")
        
        if self.mqtt_client is not None:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
        
        logger.info("Door Sentry cleanup complete")


# Flask application
app = Flask(__name__)

# Global Door Sentry instance
door_sentry = None


@app.route('/video_feed')
def video_feed():
    """
    Video streaming route.
    
    Returns:
        Response: Multipart MJPEG stream
    """
    global door_sentry
    
    if door_sentry is None:
        return "Door Sentry not initialized", 500
    
    return Response(
        door_sentry.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/health')
def health():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    global door_sentry
    
    if door_sentry is None:
        return {"status": "error", "message": "Door Sentry not initialized"}, 500
    
    return {
        "status": "ok",
        "service": "door_sentry",
        "known_faces": len(door_sentry.auth.get_known_faces())
    }


def main():
    """Main entry point."""
    global door_sentry
    
    logger.info("=" * 60)
    logger.info("Door Sentry Microservice Starting")
    logger.info("=" * 60)
    
    try:
        # Initialize Door Sentry
        door_sentry = DoorSentry()
        
        # Get port from environment
        port = int(os.getenv('DOOR_SENTRY_PORT', 5001))
        
        logger.info(f"Starting Flask server on port {port}...")
        logger.info(f"Video feed available at: http://localhost:{port}/video_feed")
        logger.info(f"Health check available at: http://localhost:{port}/health")
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
    finally:
        if door_sentry is not None:
            door_sentry.cleanup()


if __name__ == "__main__":
    main()
