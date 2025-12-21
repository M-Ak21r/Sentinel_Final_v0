import os
import sys
import json
import base64
from datetime import datetime
import logging
import cv2

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'Shared'))
from libs.file_utils import (
    safe_image_write, safe_video_writer, ensure_directory
)
from database.mongo_manager import MongoManager

class DataStorage:
    def __init__(self):
        self.logger = self.setup_logging()
        
        # Initialize MongoDB connection
        self.mongo = MongoManager()
        
        self.setup_storage()
    
    def setup_logging(self):
        """Setup logging for data storage"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data_storage.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def setup_storage(self):
        """Setup file-based storage for evidence"""
        try:
            # Create directories for storing evidence
            directories = ['evidence/images', 'evidence/videos']
            for directory in directories:
                ensure_directory(directory)
            
            self.logger.info("File storage setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up file storage: {e}")
    
    def _get_base64_image(self, file_path):
        """
        Convert an image file to Base64 data URI.
        
        Prefers thumbnail version (_thumb.jpg) for smaller payload.
        Falls back to original if thumbnail doesn't exist.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            str: Base64 data URI (data:image/jpeg;base64,...) or None
        """
        if not file_path:
            return None
        
        try:
            # Try thumbnail first (smaller file size)
            thumb_path = file_path.replace('.jpg', '_thumb.jpg')
            
            if os.path.exists(thumb_path):
                with open(thumb_path, 'rb') as f:
                    image_data = f.read()
                    encoded = base64.b64encode(image_data).decode('utf-8')
                    return f"data:image/jpeg;base64,{encoded}"
            
            # Fallback to original image
            elif os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                    encoded = base64.b64encode(image_data).decode('utf-8')
                    return f"data:image/jpeg;base64,{encoded}"
            
            else:
                self.logger.warning(f"Image file not found: {file_path}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error encoding image to Base64: {e}")
            return None
    
    def log_security_event(self, event_type, person_name=None, confidence=0, location="front_door", info="", image_path=None):
        """Log security events to MongoDB"""
        try:
            # Get events collection
            events_collection = self.mongo.get_collection('events')
            
            if events_collection is None:
                self.logger.error("Failed to get events collection from MongoDB in log_security_event() (check connection status)")
                return
            
            # Generate Base64 snapshot if image path provided
            snapshot_url = None
            if image_path:
                snapshot_url = self._get_base64_image(image_path)
            
            # Create document matching Web Interface schema
            event_document = {
                "topic": "security/door/event",
                "level": "level1",
                "cameraId": location,
                "model": "face_auth",
                "event": event_type,
                "confidence": confidence,
                "snapshotUrl": snapshot_url,
                "status": f"Detected {person_name}" if person_name else event_type,
                "raw": {
                    "person_name": person_name,
                    "info": info
                },
                "createdAt": datetime.now()
            }
            
            # Insert into MongoDB
            result = events_collection.insert_one(event_document)
            self.logger.info(f"Security event logged to MongoDB: {event_type} - {person_name} (ID: {result.inserted_id})")
            
        except Exception as e:
            self.logger.error(f"Error logging security event: {e}")
    
    def log_alert(self, alert_type, severity, description, action_taken="", image_path=None):
        """Log alerts to MongoDB with level3 (Critical)"""
        try:
            # Get events collection
            events_collection = self.mongo.get_collection('events')
            
            if events_collection is None:
                self.logger.error("Failed to get events collection from MongoDB in log_alert() (check connection status)")
                return
            
            # Generate Base64 snapshot if image path provided
            snapshot_url = None
            if image_path:
                snapshot_url = self._get_base64_image(image_path)
            
            # Create document for critical alert
            alert_document = {
                "topic": "security/door/event",
                "level": "level3",  # Critical
                "cameraId": "front_door",
                "model": "face_auth",
                "event": f"ALERT: {alert_type}",
                "confidence": None,
                "snapshotUrl": snapshot_url,
                "status": description,
                "raw": {
                    "alert_type": alert_type,
                    "severity": severity,
                    "description": description,
                    "action_taken": action_taken
                },
                "createdAt": datetime.now()
            }
            
            # Insert into MongoDB
            result = events_collection.insert_one(alert_document)
            self.logger.warning(f"Alert logged to MongoDB: {alert_type} - {severity} - {description} (ID: {result.inserted_id})")
            
        except Exception as e:
            self.logger.error(f"Error logging alert: {e}")
    
    def save_evidence_image(self, frame, event_type, person_name="unknown"):
        """Save evidence images with timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evidence/images/{event_type}_{person_name}_{timestamp}.jpg"
            
            # Create thumbnail
            thumbnail = cv2.resize(frame, (320, 240))
            
            # Use safe image write with verification
            if not safe_image_write(filename, frame, cv2):
                self.logger.error(f"Failed to save main evidence image: {filename}")
                return None
            
            if not safe_image_write(filename.replace(".jpg", "_thumb.jpg"), thumbnail, cv2):
                self.logger.warning(f"Failed to save thumbnail for: {filename}")
            
            # Log the evidence save to MongoDB
            self.log_security_event(
                event_type=f"EVIDENCE_SAVED_{event_type}",
                person_name=person_name,
                confidence=None,  # Not applicable for evidence logging
                location="front_door",
                info=f"Saved image: {filename}",
                image_path=filename
            )
            
            return filename
            
        except Exception as e:
            self.logger.error(f"Error saving evidence image: {e}")
            return None

    def save_evidence_clip(self, frames, event_type, person_name="unknown", fps=20):
        """Save a short video clip (AVI) as evidence.

        Args:
            frames: list of BGR numpy arrays
            event_type: short event name to include in filename
            person_name: label for filename
            fps: frames per second for the output video
        Returns:
            filename (str) or None
        """
        try:
            if not frames:
                self.logger.error("No frames provided to save_evidence_clip")
                return None

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evidence/videos/{event_type}_{person_name}_{timestamp}.avi"

            h, w = frames[0].shape[:2]
            # Use MJPG codec for wide compatibility
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            
            # Use context manager to ensure VideoWriter is always released
            with safe_video_writer(filename, fourcc, fps, (w, h), cv2) as out:
                for f in frames:
                    # Ensure frame has same size
                    if f.shape[0] != h or f.shape[1] != w:
                        f = cv2.resize(f, (w, h))
                    out.write(f)

            # Also save a thumbnail image
            thumb = cv2.resize(frames[len(frames)//2], (320, 240))
            thumb_name = filename.replace('.avi', '_thumb.jpg')
            safe_image_write(thumb_name, thumb, cv2)

            # Log the evidence save to MongoDB
            self.log_security_event(
                event_type=f"VIDEO_{event_type}",
                person_name=person_name,
                confidence=None,  # Not applicable for evidence logging
                location="front_door",
                info=f"Saved clip: {filename}"
            )

            self.logger.info(f"Saved evidence clip: {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"Error saving evidence clip: {e}")
            return None

    def queue_clip_for_gesture(self, clip_path, bbox=None):
        """Copy an existing clip into the gesture worker input queue and write metadata.

        Args:
            clip_path: path to an existing video clip
            bbox: optional face bbox tuple (x,y,w,h) to include as metadata

        Returns:
            queue_path (str) or None
        """
        # Validate
        if not os.path.exists(clip_path):
            self.logger.error(f"Clip to queue not found: {clip_path}")
            return None

        try:
            import shutil, uuid, json
            uid = uuid.uuid4().hex
            dest = f"evidence/gesture_queue/incoming/gesture_{uid}.avi"
            shutil.copy2(clip_path, dest)

            # Write metadata file with same uid
            meta = {
                'clip': dest,
                'bbox': bbox,
                'timestamp': datetime.now().isoformat()
            }
            meta_path = dest.replace('.avi', '.json')
            with open(meta_path, 'w') as f:
                json.dump(meta, f)

            self.logger.info(f"Queued clip for gesture analysis: {dest}")
            return dest
        except Exception as e:
            self.logger.error(f"Error queueing clip for gesture: {e}")
            return None