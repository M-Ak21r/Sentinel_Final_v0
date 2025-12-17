# Interior Watch Service - main.py

**Production-ready microservice for interior room monitoring with theft detection and evidence management.**

## Overview

The Interior Watch service (`main.py`) is the refactored Level 2 system that monitors interior spaces for theft detection. It uses YOLOv8 for object tracking, InsightFace for identity verification, and provides a REST API for evidence management.

## Key Features

### 🔍 Theft Detection ("Ghost Protocol")
- Real-time tracking of assets (laptops, cell phones) using YOLO persistent tracking
- Detects when tracked assets disappear for >30 frames (~1 second)
- Proximity-based suspect identification (<150 pixels from last known location)
- Smart filtering to reduce false positives

### 🔐 Identity Verification
- Integrates with shared `FaceAuthenticator` library
- Authorized personnel can move assets without triggering alarms
- Unknown/unauthorized persons trigger immediate alerts
- Suspect verification before alarm activation

### 📹 Evidence Recording
- Automatic video recording when theft alarm triggers
- Timestamped evidence files: `theft_evidence_YYYYMMDD_HHMMSS.mp4`
- Saved to `Shared/data/evidence/` directory
- Continues recording until manual stop via MQTT

### 📡 MQTT Integration
- Publishes theft alerts: `{"level": 2, "type": "THEFT", "msg": "..."}`
- Listens for stop commands: `{"target": "interior", "action": "STOP_ALARM"}`
- Real-time event streaming to web dashboard

### 🌐 REST API
- MJPEG video streaming with annotated frames
- Evidence file listing with metadata (size, timestamp)
- Direct video file serving for playback
- Health check endpoint for monitoring

## Installation

### Prerequisites
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3 python3-pip cmake libopenblas-dev liblapack-dev

# For GPU acceleration (optional)
# Install CUDA and cuDNN
```

### Python Dependencies
```bash
cd /home/runner/work/Sentinel_Final_v0/Sentinel_Final_v0/Sentinel_Unified
pip install -r requirements.txt
```

### Configuration
1. Copy `.env.example` to `.env` in the root directory:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```env
# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883

# Interior Watch Configuration
INTERIOR_CAMERA_INDEX=1          # Camera device index
INTERIOR_WATCH_PORT=5002         # Flask server port
SHARED_DATA_PATH=./Sentinel_Unified/Shared/data
```

3. Ensure YOLO model exists:
```bash
# The service will look for the model at:
# Sentinel_Unified/Shared/models/yolo11n.pt
# If not found, it will attempt to download automatically
```

4. Set up authorized faces:
```bash
# Add authorized personnel photos to:
# Sentinel_Unified/Shared/data/authorized_faces/<person_name>/
# Example:
mkdir -p Sentinel_Unified/Shared/data/authorized_faces/John_Doe
cp john_photo1.jpg Sentinel_Unified/Shared/data/authorized_faces/John_Doe/
```

## Usage

### Starting the Service
```bash
cd Sentinel_Unified/Services/Interior_Watch
python main.py
```

The service will:
1. Initialize FaceAuthenticator with authorized faces
2. Load YOLO model for object detection
3. Connect to MQTT broker
4. Start Flask server on configured port
5. Begin monitoring camera feed

### Accessing the Service

**Video Stream:**
```
http://localhost:5002/video_feed
```

**Health Check:**
```bash
curl http://localhost:5002/health
```

Response:
```json
{
  "status": "ok",
  "service": "interior_watch",
  "alarm_active": false,
  "recording_active": false,
  "known_faces": 3,
  "tracked_assets": 2
}
```

**List Evidence Files:**
```bash
curl http://localhost:5002/api/recordings
```

Response:
```json
[
  {
    "filename": "theft_evidence_20231217_143022.mp4",
    "size_mb": 12.45,
    "timestamp": "2023-12-17T14:30:22"
  },
  ...
]
```

**Download Evidence:**
```
http://localhost:5002/api/recordings/theft_evidence_20231217_143022.mp4
```

### MQTT Commands

**Stop Alarm:**
```bash
mosquitto_pub -h localhost -t sentinel/commands -m '{"target": "interior", "action": "STOP_ALARM"}'
```

**Subscribe to Alerts:**
```bash
mosquitto_sub -h localhost -t sentinel/alerts
```

Alert format:
```json
{
  "level": 2,
  "type": "THEFT",
  "msg": "Theft detected! Asset 42 taken by unauthorized person",
  "timestamp": "2023-12-17T14:30:22.123456",
  "source": "interior_watch"
}
```

## System Architecture

### InteriorWatchService Class

**Initialization:**
- `FaceAuthenticator`: Face recognition for identity verification
- `YOLO`: Object detection model (yolo11n.pt)
- `MQTT Client`: For alerts and commands
- `Camera`: OpenCV VideoCapture
- `State Variables`: alarm_active, recording_active, asset_states

**Core Methods:**

1. **process_frame()** - The Brain
   - Runs YOLO tracking with persistence
   - Updates asset state tracking
   - Implements "Ghost Protocol" theft detection
   - Verifies suspects with FaceAuthenticator
   - Records evidence if alarm is active
   - Annotates frames with visualizations

2. **start_recording()** - Evidence Capture
   - Creates timestamped video file
   - Initializes cv2.VideoWriter
   - Manages recording state

3. **_handle_mqtt_command()** - Command Processing
   - Listens on sentinel/commands topic
   - Handles STOP_ALARM command
   - Releases video writer
   - Resets alarm state

### Theft Detection Algorithm ("Ghost Protocol")

```
FOR each frame:
  1. Run YOLO tracking on frame
  2. Update asset_states dictionary:
     - Track laptops (class 63) and phones (class 67)
     - Store: last_seen frame, last_pos, missing_frames
  
  3. FOR each tracked asset:
     IF asset not seen in current frame:
       Increment missing_frames
       
       IF missing_frames == FRAMES_UNTIL_THEFT (30):
         Find closest person to asset's last_pos
         
         IF person within PROXIMITY_THRESHOLD (150px):
           Crop person from frame
           Run FaceAuthenticator.identify_face(crop)
           
           IF face is authorized:
             Log "Authorized movement"
             Remove asset from tracking
           ELSE:
             Activate alarm
             Start recording
             Publish MQTT alert
             Draw red box on suspect
```

## Configuration Constants

Located at the top of `main.py`:

```python
# YOLO class IDs
CLASS_PERSON = 0
CLASS_LAPTOP = 63
CLASS_CELL_PHONE = 67

# Theft detection
FRAMES_UNTIL_THEFT = 30          # ~1 second at 30fps
PROXIMITY_THRESHOLD = 150        # pixels
STALE_ASSET_MULTIPLIER = 3       # cleanup threshold

# Alert levels
ALERT_LEVEL_CRITICAL = 1
ALERT_LEVEL_WARNING = 2
ALERT_LEVEL_INFO = 3

# Recording
EVIDENCE_FILENAME_PREFIX = "theft_evidence"

# Visualization
FLASH_INTERVAL_FRAMES = 10       # Alarm flash rate
ALARM_OVERLAY_HEIGHT = 60        # pixels
ALARM_OVERLAY_ALPHA = 0.3        # transparency
```

## Visualization

**Asset Tracking:**
- Green boxes around tracked assets
- Labels: "Laptop ID:42" or "Phone ID:17"

**Theft Detection:**
- Red boxes around suspects
- "SUSPECT!" label

**Alarm State:**
- Flashing red overlay at top of screen
- "!!! ALARM TRIGGERED !!!" text
- Flashes every 10 frames (configurable)

**Frame Info:**
- Timestamp overlay at bottom

## Troubleshooting

### Camera Not Opening
```
Error: Failed to open camera
```
**Solution:** Check `INTERIOR_CAMERA_INDEX` in .env. Try values 0, 1, 2.

### YOLO Model Not Found
```
Error: Failed to load YOLO model
```
**Solution:** 
- Ensure `Shared/models/yolo11n.pt` exists
- Service will attempt auto-download as fallback
- Manually download: `yolo task=detect mode=predict model=yolo11n.pt`

### Face Recognition Not Working
```
Warning: No faces detected
```
**Solution:**
- Ensure authorized_faces directory has images
- Check face image quality (well-lit, frontal view)
- Verify FaceAuthenticator initialization logs

### MQTT Connection Failed
```
Error: Failed to connect to MQTT broker
```
**Solution:**
- Check MQTT_BROKER and MQTT_PORT in .env
- Verify mosquitto is running: `sudo systemctl status mosquitto`
- Service continues without MQTT (alerts won't work)

### No Recording Created
```
Recording active but no file created
```
**Solution:**
- Check write permissions on evidence directory
- Verify disk space available
- Check logs for video writer errors

## Performance Optimization

**For Better FPS:**
- Reduce camera resolution in __init__:
  ```python
  self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
  self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
  ```

**For Better Accuracy:**
- Use larger YOLO model (yolo11s.pt, yolo11m.pt)
- Increase camera resolution
- Adjust similarity_threshold in FaceAuthenticator

**For Less Storage:**
- Reduce recording FPS
- Use better compression codec
- Implement automatic evidence cleanup

## Integration with Web Interface

The service is designed to work with the Sentinel Web Interface:

1. **Video Feed Integration:**
   ```html
   <img src="http://localhost:5002/video_feed" />
   ```

2. **Evidence Browser:**
   ```javascript
   fetch('http://localhost:5002/api/recordings')
     .then(res => res.json())
     .then(recordings => {
       // Display list of recordings
     });
   ```

3. **Alarm Control:**
   ```javascript
   // Via MQTT
   mqtt.publish('sentinel/commands', 
     JSON.stringify({target: 'interior', action: 'STOP_ALARM'})
   );
   ```

## Security Considerations

✅ **Implemented:**
- No hardcoded credentials
- Configuration via environment variables
- Path traversal protection in file serving
- MQTT authentication support (configure in broker)

⚠️ **Recommended:**
- Use HTTPS for Flask (add reverse proxy)
- Enable MQTT TLS/SSL
- Implement JWT authentication for API endpoints
- Regular evidence file cleanup policy
- Audit logs for all alarm events

## License

Part of the Sentinel Unified System.
Author: Sentinel System
