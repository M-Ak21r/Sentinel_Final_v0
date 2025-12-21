"""
Interior Watch Microservice
============================
This service monitors the interior room and handles:
- Theft Detection: Track assets (laptops/phones) using YOLOv8
- Identity Check: Verify suspects using FaceAuthenticator
- Evidence API: Provide REST API for browsing recorded theft videos

Author: Sentinel System
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

import cv2
import json
import time
import logging
import signal
from collections import deque
from datetime import datetime
from flask import Flask, Response, jsonify, send_from_directory
from dotenv import load_dotenv
import paho.mqtt.client as mqtt
from ultralytics import YOLO
import numpy as np

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


# YOLO class IDs for objects of interest
CLASS_PERSON = 0
CLASS_LAPTOP = 63
CLASS_CELL_PHONE = 67
ASSET_CLASSES = {CLASS_LAPTOP, CLASS_CELL_PHONE}

# Theft detection configuration
FRAMES_UNTIL_THEFT = 30  # Asset must be missing for 30 frames (~1 second)
PROXIMITY_THRESHOLD = 300  # Pixels - how close a person must be to the asset
STALE_ASSET_MULTIPLIER = 3  # Multiplier for determining when to clean up stale assets

# Alert level constants
ALERT_LEVEL_CRITICAL = 1
ALERT_LEVEL_WARNING = 2
ALERT_LEVEL_INFO = 3

# Video recording constants
EVIDENCE_FILENAME_PREFIX = "theft_evidence"
MIN_RECORDING_FRAMES = 300  # Minimum recording duration: 10 seconds at 30 FPS

# Visualization constants
FLASH_INTERVAL_FRAMES = 10  # Flash every N frames
ALARM_OVERLAY_HEIGHT = 60  # Height of alarm overlay in pixels
ALARM_OVERLAY_ALPHA = 0.3  # Transparency of alarm overlay
ALARM_BACKGROUND_ALPHA = 0.7  # Transparency of background when alarm is active


class InteriorWatchService:
    """
    Interior Watch microservice for monitoring the interior room.
    
    This class manages:
    - YOLO-based asset tracking (laptops, phones)
    - Theft detection using "Ghost Protocol"
    - Face authentication for suspects
    - Video evidence recording
    - MQTT communication for alerts and control
    """
    
    def __init__(self):
        """Initialize Interior Watch with YOLO, face auth, and MQTT."""
        logger.info("Initializing Interior Watch...")
        
        # Load configuration from environment
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', 1883))
        self.camera_index = int(os.getenv('INTERIOR_CAMERA_INDEX', 1))
        self.shared_data_path = os.getenv('SHARED_DATA_PATH', 
                                         os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                                      '../../Shared/data')))
        
        # Initialize state variables
        self.alarm_active = False
        self.recording_active = False
        self.asset_states = {}  # {track_id: {'class': int, 'last_seen': int, 'last_pos': (x, y), 'missing_frames': int}}
        self.frame_count = 0
        self.video_writer = None
        self.current_recording_path = None
        self.running = False
        self.process_every_n_frames = 2  # Process YOLO every 2nd frame for better FPS
        self.recording_frame_count = 0  # Track frames recorded for minimum duration enforcement
        
        # Initialize ring buffer for pre-event recording (stores ~5 seconds at 30 FPS)
        self.video_buffer = deque(maxlen=150)
        
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
        
        # Initialize YOLO model
        logger.info("Initializing YOLO model...")
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                   '../../Shared/models/yolo11n.pt'))
        try:
            self.model = YOLO(model_path)
            logger.info(f"YOLO model loaded from: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model from {model_path}: {e}")
            # Try alternative path
            try:
                self.model = YOLO("yolo11n.pt")  # Will download if not available
                logger.info("YOLO model loaded (downloaded)")
            except Exception as e2:
                logger.error(f"Failed to load YOLO model: {e2}")
                raise
        
        # Initialize camera
        logger.info(f"Opening camera (index: {self.camera_index})...")
        self.camera = cv2.VideoCapture(self.camera_index)
        if not self.camera.isOpened():
            logger.error("Failed to open camera")
            raise RuntimeError("Failed to open camera")
        
        # Set camera properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        logger.info("Camera opened successfully")
        
        # Get actual camera properties
        self.frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = int(self.camera.get(cv2.CAP_PROP_FPS)) or 30
        
        # Initialize MQTT client
        logger.info(f"Setting up MQTT client (broker: {self.mqtt_broker}:{self.mqtt_port})...")
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="interior_watch")
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._handle_mqtt_command
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            logger.info("MQTT client connected and loop started")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            logger.warning("Continuing without MQTT - alerts and commands will not work")
        
        # Create evidence directory if it doesn't exist
        self.evidence_dir = os.path.join(self.shared_data_path, 'evidence')
        os.makedirs(self.evidence_dir, exist_ok=True)
        logger.info(f"Evidence directory: {self.evidence_dir}")
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        logger.info("Signal handlers registered for graceful shutdown")
        
        logger.info("Interior Watch initialized successfully")
    
    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (SIGINT/SIGTERM).
        
        When a signal is received, set self.running = False to allow
        the main loop to exit naturally and execute the cleanup logic.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
        logger.info(f"Received {signal_name} - initiating graceful shutdown...")
        self.running = False
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT client connects to broker."""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
            # Subscribe to commands topic
            client.subscribe("sentinel/commands")
            logger.info("Subscribed to sentinel/commands")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def _handle_mqtt_command(self, client, userdata, msg, properties=None):
        """
        Handle incoming MQTT commands.
        
        Listens for commands like:
        {"target": "interior", "action": "STOP_ALARM"}
        {"target": "all", "action": "RELOAD_FACES"}
        """
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            logger.info(f"Received MQTT message on {msg.topic}: {payload}")
            
            # Check if this command is for interior watch
            if payload.get('target') == 'interior':
                action = payload.get('action')
                
                if action == 'STOP_ALARM':
                    logger.info("Received STOP_ALARM command - silencing alarm")
                    self.alarm_active = False
                    
                    # Enforce minimum recording duration before stopping
                    if self.recording_frame_count >= MIN_RECORDING_FRAMES:
                        # Release video writer if recording
                        if self.video_writer is not None:
                            self.video_writer.release()
                            self.video_writer = None
                            self.recording_active = False
                            self.recording_frame_count = 0  # Reset frame counter
                            logger.info(f"Recording stopped: {self.current_recording_path}")
                            logger.info("Evidence saved successfully")
                    else:
                        # Continue recording until minimum duration is met
                        frames_remaining = MIN_RECORDING_FRAMES - self.recording_frame_count
                        seconds_remaining = frames_remaining / self.fps
                        logger.info(f"Minimum recording duration not met. Need {frames_remaining} more frames (~{seconds_remaining:.1f} seconds) before stopping.")
                    
                    logger.info("Alarm silenced by user")
            
            # Check if this command is for all services (hot-reload faces)
            elif payload.get('target') == 'all' and payload.get('action') == 'RELOAD_FACES':
                print(f"[{self.__class__.__name__}] Command received: Reloading faces...")
                logger.info("[System] Hot-reloading face database...")
                self.auth.reload_faces()
                logger.info(f"[System] Face database reloaded: {len(self.auth.get_known_faces())} faces")
                    
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode MQTT message: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _is_mqtt_connected(self):
        """
        Check if MQTT client is connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self.mqtt_client is not None and self.mqtt_client.is_connected()
    
    def _publish_alert(self, level, alert_type, message):
        """
        Publish MQTT alert.
        
        Args:
            level (int): Alert level (1=critical, 2=warning, 3=info)
            alert_type (str): Type of alert (e.g., "THEFT")
            message (str): Alert message
        """
        if not self._is_mqtt_connected():
            logger.warning("MQTT client not connected, cannot publish alert")
            return
        
        try:
            payload = {
                "level": level,
                "type": alert_type,
                "msg": message,
                "timestamp": datetime.now().isoformat(),
                "source": "interior_watch"
            }
            result = self.mqtt_client.publish(
                "sentinel/alerts",
                json.dumps(payload),
                qos=1
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published alert: {alert_type} - {message}")
            else:
                logger.warning(f"Failed to publish alert: {result.rc}")
        except Exception as e:
            logger.error(f"Error publishing alert: {e}")
    
    def start_recording(self):
        """
        Start recording video evidence.
        
        Creates a new video file with timestamp in the evidence directory.
        Uses H.264 codec (avc1) for better web playback compatibility, with
        fallback to mp4v if avc1 is not available.
        
        Dumps pre-event buffer frames to capture footage before the theft trigger.
        """
        if self.video_writer is not None:
            # Already recording
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{EVIDENCE_FILENAME_PREFIX}_{timestamp}.mp4"
        self.current_recording_path = os.path.join(self.evidence_dir, filename)
        
        # Try H.264 codec first (avc1) as it's more robust for web playback
        fourcc_avc1 = cv2.VideoWriter_fourcc(*'avc1')
        self.video_writer = cv2.VideoWriter(
            self.current_recording_path,
            fourcc_avc1,
            self.fps,
            (self.frame_width, self.frame_height)
        )
        
        # Check if avc1 codec worked
        if not self.video_writer.isOpened():
            logger.warning("H.264 codec (avc1) not available, falling back to mp4v")
            self.video_writer.release()
            
            # Fallback to mp4v codec
            fourcc_mp4v = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                self.current_recording_path,
                fourcc_mp4v,
                self.fps,
                (self.frame_width, self.frame_height)
            )
        
        if self.video_writer.isOpened():
            self.recording_active = True
            self.recording_frame_count = 0  # Reset frame counter
            
            # Dump pre-event buffer frames to capture "Pre-Theft" footage
            logger.info(f"Dumping {len(self.video_buffer)} pre-event frames from ring buffer...")
            try:
                for buffered_frame in self.video_buffer:
                    self.video_writer.write(buffered_frame)
            except Exception as e:
                logger.error(f"Error writing buffered frames: {e}")
                # Continue anyway - some pre-event footage is better than none
            
            # Clear buffer after dumping to avoid duplicate frames
            self.video_buffer.clear()
            
            # Debug logging to help diagnose file creation issues
            logger.info(f"Started recording: {self.current_recording_path}")
            logger.info(f"Video writer opened: {self.video_writer.isOpened()}")
        else:
            logger.error(f"Failed to start recording: {self.current_recording_path}")
            logger.error(f"Video writer opened: {self.video_writer.isOpened()}")
            self.video_writer = None
    
    def _calculate_distance(self, pos1, pos2):
        """
        Calculate Euclidean distance between two points.
        
        Args:
            pos1 (tuple): (x, y) coordinates
            pos2 (tuple): (x, y) coordinates
        
        Returns:
            float: Distance in pixels
        """
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _get_center(self, bbox):
        """
        Get center point of a bounding box.
        
        Args:
            bbox (list): [x1, y1, x2, y2]
        
        Returns:
            tuple: (center_x, center_y)
        """
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def _point_in_bbox(self, point, bbox):
        """
        Check if a point is inside a bounding box.
        
        Args:
            point (tuple): (x, y) coordinates
            bbox (list): [x1, y1, x2, y2]
        
        Returns:
            bool: True if point is inside bbox, False otherwise
        """
        x, y = point
        x1, y1, x2, y2 = bbox
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def process_frame(self):
        """
        Process a single frame - the core brain of theft detection.
        
        Steps:
        1. YOLO tracking for assets and persons
        2. "Ghost Protocol" - detect missing assets
        3. Verify suspects using face authentication
        4. Record evidence if alarm is active
        5. Visualize results
        
        Returns:
            bytes: Annotated frame as JPEG bytes, or None if error
        """
        # Read frame from camera
        ret, frame = self.camera.read()
        if not ret or frame is None:
            logger.warning("Failed to read frame from camera")
            return None
        
        self.frame_count += 1
        annotated_frame = frame.copy()
        
        # Step 1: YOLO Tracking (skip frames for better FPS)
        # Only process detection every Nth frame, but always stream
        if self.frame_count % self.process_every_n_frames == 0:
            try:
                results = self.model.track(frame, persist=True, verbose=False)
            
                if results and len(results) > 0:
                    result = results[0]
                    
                    # Get detections
                    if result.boxes is not None and len(result.boxes) > 0:
                        boxes = result.boxes
                        
                        # Track which assets we've seen this frame
                        seen_asset_ids = set()
                        detected_persons = []
                        
                        # Process each detection
                        for i, box in enumerate(boxes):
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            xyxy = box.xyxy[0].cpu().numpy()
                            x1, y1, x2, y2 = map(int, xyxy)
                            
                            # Get track ID if available
                            if box.id is not None:
                                track_id = int(box.id[0])
                            else:
                                track_id = None
                            
                            # Track assets (laptops and cell phones)
                            if cls in ASSET_CLASSES and track_id is not None:
                                seen_asset_ids.add(track_id)
                                center = self._get_center([x1, y1, x2, y2])
                                
                                # Update asset state
                                if track_id not in self.asset_states:
                                    self.asset_states[track_id] = {
                                        'class': cls,
                                        'last_seen': self.frame_count,
                                        'last_pos': center,
                                        'missing_frames': 0
                                    }
                                else:
                                    self.asset_states[track_id]['last_seen'] = self.frame_count
                                    self.asset_states[track_id]['last_pos'] = center
                                    self.asset_states[track_id]['missing_frames'] = 0
                                
                                # Draw green box for tracked assets
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                label = f"{'Laptop' if cls == CLASS_LAPTOP else 'Phone'} ID:{track_id}"
                                cv2.putText(annotated_frame, label, (x1, y1 - 10),
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
                            # Track persons
                            elif cls == CLASS_PERSON:
                                detected_persons.append({
                                    'bbox': [x1, y1, x2, y2],
                                    'center': self._get_center([x1, y1, x2, y2]),
                                    'conf': conf
                                })
                        
                        # Step 2: "Ghost Protocol" - Detect missing assets
                        for asset_id, asset_info in list(self.asset_states.items()):
                            if asset_id not in seen_asset_ids:
                                # Asset is missing from this frame
                                asset_info['missing_frames'] += 1
                                
                                # Check if asset has been missing long enough to trigger theft
                                if asset_info['missing_frames'] == FRAMES_UNTIL_THEFT:
                                    logger.warning(f"POTENTIAL THEFT: Asset {asset_id} missing for {FRAMES_UNTIL_THEFT} frames")
                                    
                                    # Step 3: Find suspect using containment check first, then proximity
                                    last_pos = asset_info['last_pos']
                                    closest_person = None
                                    closest_distance = float('inf')
                                    
                                    # First, check if the asset's last position is inside any person's bounding box
                                    for person in detected_persons:
                                        if self._point_in_bbox(last_pos, person['bbox']):
                                            # Asset position is inside this person's bounding box - strong suspect!
                                            closest_person = person
                                            closest_distance = 0  # Direct containment
                                            logger.debug(f"Asset {asset_id} last position is inside person's bounding box")
                                            break
                                    
                                    # If no containment found, fallback to proximity check with relaxed threshold
                                    if closest_person is None:
                                        for person in detected_persons:
                                            distance = self._calculate_distance(last_pos, person['center'])
                                            if distance < closest_distance:
                                                closest_distance = distance
                                                if distance < PROXIMITY_THRESHOLD:
                                                    closest_person = person
                                    
                                    if closest_person:
                                        # We have a suspect - verify identity
                                        x1, y1, x2, y2 = closest_person['bbox']
                                        suspect_crop = frame[y1:y2, x1:x2]
                                        
                                        if suspect_crop.size > 0:
                                            # Run face authentication
                                            faces = self.auth.identify_face(suspect_crop)
                                            
                                            is_authorized = False
                                            suspect_name = "Unknown"
                                            
                                            if faces and len(faces) > 0:
                                                face = faces[0]
                                                is_authorized = face['is_authorized']
                                                suspect_name = face['name']
                                            
                                            if is_authorized:
                                                # Authorized person - log and ignore
                                                logger.info(f"Authorized movement by {suspect_name}")
                                                # Reset asset state since it's authorized
                                                del self.asset_states[asset_id]
                                            else:
                                                # UNAUTHORIZED THEFT DETECTED!
                                                logger.error(f"THEFT DETECTED! Unauthorized person near asset {asset_id}")
                                                
                                                # Activate alarm
                                                self.alarm_active = True
                                                
                                                # Start recording if not already
                                                if not self.recording_active:
                                                    self.start_recording()
                                                
                                                # Publish MQTT alert
                                                self._publish_alert(
                                                    level=ALERT_LEVEL_WARNING,
                                                    alert_type="THEFT",
                                                    message=f"Theft detected! Asset {asset_id} taken by unauthorized person"
                                                )
                                                
                                                # Draw red box around suspect
                                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                                                cv2.putText(annotated_frame, "SUSPECT!", (x1, y1 - 10),
                                                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                                    else:
                                        # No person nearby - might be a false positive
                                        logger.debug(f"Closest person was {closest_distance:.1f}px away (Threshold: {PROXIMITY_THRESHOLD}px)")
                                        logger.info(f"Asset {asset_id} disappeared but no suspect nearby")
                            
                            # Clean up old asset states (missing for too long)
                            if asset_info['missing_frames'] > FRAMES_UNTIL_THEFT * STALE_ASSET_MULTIPLIER:
                                logger.info(f"Removing stale asset {asset_id} from tracking")
                                del self.asset_states[asset_id]
            
            except Exception as e:
                logger.error(f"Error during YOLO tracking: {e}")
        else:
            # Frame skipped - just stream without detection
            pass
        
        # Step 4: Recording
        # Always buffer frames for pre-event recording
        self.video_buffer.append(annotated_frame.copy())
        
        # Write to video file if recording is active
        if self.recording_active and self.video_writer is not None:
            self.video_writer.write(annotated_frame)
            self.recording_frame_count += 1
            
            # Check if minimum recording duration is met and alarm is not active
            if not self.alarm_active and self.recording_frame_count >= MIN_RECORDING_FRAMES:
                # Stop recording since minimum duration is met and alarm is cleared
                self.video_writer.release()
                self.video_writer = None
                self.recording_active = False
                logger.info(f"Recording stopped after {self.recording_frame_count} frames (minimum duration met): {self.current_recording_path}")
                logger.info("Evidence saved successfully")
                self.recording_frame_count = 0
        
        # Add timestamp
        timestamp_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated_frame, timestamp_text, (10, annotated_frame.shape[0] - 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Add FPS counter for monitoring performance
        fps_text = f"Frame: {self.frame_count} (Processing every {self.process_every_n_frames})"
        cv2.putText(annotated_frame, fps_text, (10, annotated_frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Flash "ALARM TRIGGERED" if alarm is active
        if self.alarm_active:
            # Create a flashing effect
            if (self.frame_count // FLASH_INTERVAL_FRAMES) % 2 == 0:  # Flash every N frames
                # Draw red overlay
                overlay = annotated_frame.copy()
                cv2.rectangle(overlay, (0, 0), (annotated_frame.shape[1], ALARM_OVERLAY_HEIGHT), (0, 0, 255), -1)
                cv2.addWeighted(overlay, ALARM_OVERLAY_ALPHA, annotated_frame, ALARM_BACKGROUND_ALPHA, 0, annotated_frame)
                
                # Draw text
                text = "!!! ALARM TRIGGERED !!!"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.2, 3)[0]
                text_x = (annotated_frame.shape[1] - text_size[0]) // 2
                cv2.putText(annotated_frame, text, (text_x, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        
        # Encode frame as JPEG with optimized quality (70% instead of default 95%)
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
    
    def get_recordings(self):
        """
        Get list of all recorded theft evidence videos.
        
        Returns:
            list: List of dictionaries with recording metadata
        """
        recordings = []
        
        try:
            if not os.path.exists(self.evidence_dir):
                return recordings
            
            for filename in os.listdir(self.evidence_dir):
                if filename.endswith('.mp4'):
                    filepath = os.path.join(self.evidence_dir, filename)
                    
                    # Get file stats
                    stat = os.stat(filepath)
                    size_mb = stat.st_size / (1024 * 1024)  # Convert to MB
                    
                    # Parse timestamp from filename
                    try:
                        # Format: theft_evidence_YYYYMMDD_HHMMSS.mp4
                        timestamp_str = filename.replace(f'{EVIDENCE_FILENAME_PREFIX}_', '').replace('.mp4', '')
                        timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                        timestamp_iso = timestamp.isoformat()
                    except Exception as e:
                        # Fallback to file modification time if parsing fails
                        logger.debug(f"Failed to parse timestamp from filename {filename}: {e}")
                        timestamp_iso = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    
                    recordings.append({
                        'filename': filename,
                        'size_mb': round(size_mb, 2),
                        'timestamp': timestamp_iso
                    })
            
            # Sort by timestamp (newest first)
            recordings.sort(key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting recordings: {e}")
        
        return recordings
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up Interior Watch...")
        self.running = False
        
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            logger.info("Video writer released")
            if self.current_recording_path:
                logger.info("Evidence saved successfully")
        
        if self.camera is not None:
            self.camera.release()
            logger.info("Camera released")
        
        if self.mqtt_client is not None:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
        
        logger.info("Interior Watch cleanup complete")


# Flask application
app = Flask(__name__)

# Global Interior Watch instance
interior_watch = None


@app.route('/video_feed')
def video_feed():
    """
    Video streaming route.
    
    Returns:
        Response: Multipart MJPEG stream
    """
    global interior_watch
    
    if interior_watch is None:
        return "Interior Watch not initialized", 500
    
    return Response(
        interior_watch.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/recordings', methods=['GET'])
def get_recordings():
    """
    Get list of all recorded theft evidence videos.
    
    Returns:
        JSON: List of recording metadata
    """
    global interior_watch
    
    if interior_watch is None:
        return jsonify({"error": "Interior Watch not initialized"}), 500
    
    recordings = interior_watch.get_recordings()
    return jsonify(recordings)


@app.route('/api/recordings/<path:filename>', methods=['GET'])
def get_recording(filename):
    """
    Serve a specific recording video file.
    
    Args:
        filename (str): Name of the video file
    
    Returns:
        File: Video file
    """
    global interior_watch
    
    if interior_watch is None:
        return "Interior Watch not initialized", 500
    
    try:
        return send_from_directory(interior_watch.evidence_dir, filename)
    except Exception as e:
        logger.error(f"Error serving recording {filename}: {e}")
        return f"Error: {str(e)}", 404


@app.route('/health')
def health():
    """
    Health check endpoint.
    
    Returns:
        dict: Health status
    """
    global interior_watch
    
    if interior_watch is None:
        return {"status": "error", "message": "Interior Watch not initialized"}, 500
    
    return {
        "status": "ok",
        "service": "interior_watch",
        "alarm_active": interior_watch.alarm_active,
        "recording_active": interior_watch.recording_active,
        "known_faces": len(interior_watch.auth.get_known_faces()),
        "tracked_assets": len(interior_watch.asset_states)
    }


def main():
    """Main entry point."""
    global interior_watch
    
    logger.info("=" * 60)
    logger.info("Interior Watch Microservice Starting")
    logger.info("=" * 60)
    
    try:
        # Initialize Interior Watch
        interior_watch = InteriorWatchService()
        
        # Get port from environment
        port = int(os.getenv('INTERIOR_WATCH_PORT', 5002))
        
        logger.info(f"Starting Flask server on port {port}...")
        logger.info(f"Video feed available at: http://localhost:{port}/video_feed")
        logger.info(f"Recordings API available at: http://localhost:{port}/api/recordings")
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
        if interior_watch is not None:
            interior_watch.cleanup()
        logger.info("Interior Watch service terminated")


if __name__ == "__main__":
    main()
