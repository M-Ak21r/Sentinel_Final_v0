# Door Sentry Microservice

## Overview

The Door Sentry microservice monitors the front door using a camera and provides:
- Real-time video streaming to the Web Interface
- Face authentication using the shared `FaceAuthenticator`
- MQTT-based door control and alerting
- Remote unlock capability via MQTT commands

## Architecture

```
Door Sentry
    ├── Camera Input (USB/Webcam)
    ├── FaceAuthenticator (Shared)
    ├── MQTT Client (Commands & Alerts)
    └── Flask Server (Video Streaming)
```

## Features

### 1. Face Authentication
- Detects faces in camera feed
- Identifies authorized users
- Visual feedback with colored bounding boxes:
  - **GREEN**: Authorized user
  - **RED**: Unknown/Unauthorized person

### 2. Automatic Door Control
- Publishes unlock command when authorized user detected
- Rate limited to once every 15 seconds per user
- MQTT Topic: `sentinel/door/control`
- Payload: `{"action": "UNLOCK", "user": "Name", "timestamp": "..."}`

### 3. Intruder Alerts
- Tracks unknown faces
- Triggers alert if unknown face persists for > 5 seconds
- MQTT Topic: `sentinel/alerts`
- Payload: `{"level": "critical", "msg": "Intruder at door", "timestamp": "..."}`

### 4. Remote Control
- Listens to MQTT commands
- Supports manual unlock from dashboard
- MQTT Topic: `sentinel/commands`
- Expected Payload: `{"target": "door", "command": "UNLOCK"}`

### 5. Video Streaming
- Provides MJPEG stream via HTTP
- Endpoint: `http://localhost:5001/video_feed`
- Includes annotated bounding boxes and timestamps

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# MQTT Configuration
MQTT_BROKER=localhost
MQTT_PORT=1883

# Camera Configuration
CAMERA_INDEX=0

# Door Sentry Configuration
DOOR_SENTRY_PORT=5001
```

See `.env.example` for a template.

## Installation

### Prerequisites

1. Python 3.8 or higher
2. USB webcam or built-in camera
3. MQTT broker (e.g., Mosquitto) running
4. Authorized face images in `Sentinel_Unified/data/authorized_faces/`

### Dependencies

Install required packages:

```bash
pip install -r Sentinel_Unified/requirements.txt
```

Key dependencies:
- `insightface` - Face recognition
- `opencv-python` - Camera and image processing
- `flask` - Web server for video streaming
- `paho-mqtt` - MQTT client
- `python-dotenv` - Environment configuration

### Face Data Setup

1. Create person directories in `Sentinel_Unified/data/authorized_faces/`:
   ```
   data/authorized_faces/
   ├── John_Doe/
   │   ├── photo1.jpg
   │   ├── photo2.jpg
   │   └── photo3.jpg
   └── Jane_Smith/
       ├── photo1.jpg
       └── photo2.jpg
   ```

2. Add multiple photos per person (3-5 recommended) for better accuracy

3. Photos should:
   - Contain only one face
   - Be well-lit
   - Show the face clearly
   - Be at least 100x100 pixels

## Usage

### Start the Service

```bash
cd Sentinel_Unified/Services/Door_Sentry
python main.py
```

### Expected Output

```
============================================================
Door Sentry Microservice Starting
============================================================
2024-12-17 10:30:00 - __main__ - INFO - Initializing Door Sentry...
2024-12-17 10:30:00 - __main__ - INFO - Initializing FaceAuthenticator...
2024-12-17 10:30:05 - __main__ - INFO - FaceAuthenticator initialized with 2 known faces
2024-12-17 10:30:05 - __main__ - INFO - Opening camera (index: 0)...
2024-12-17 10:30:05 - __main__ - INFO - Camera opened successfully
2024-12-17 10:30:05 - __main__ - INFO - Setting up MQTT client...
2024-12-17 10:30:05 - __main__ - INFO - Connected to MQTT broker successfully
2024-12-17 10:30:05 - __main__ - INFO - Door Sentry initialized successfully
2024-12-17 10:30:05 - __main__ - INFO - Starting Flask server on port 5001...
2024-12-17 10:30:05 - __main__ - INFO - Video feed available at: http://localhost:5001/video_feed
2024-12-17 10:30:05 - __main__ - INFO - Health check available at: http://localhost:5001/health
============================================================
 * Serving Flask app 'main'
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5001
```

### Access the Video Feed

Open in a browser or embed in your web interface:
```
http://localhost:5001/video_feed
```

### Health Check

Check service status:
```bash
curl http://localhost:5001/health
```

Response:
```json
{
  "status": "ok",
  "service": "door_sentry",
  "known_faces": 2
}
```

## MQTT Integration

### Published Topics

#### Door Control
- **Topic**: `sentinel/door/control`
- **QoS**: 1
- **Payload**:
  ```json
  {
    "action": "UNLOCK",
    "user": "John Doe",
    "timestamp": "2024-12-17T10:30:15.123456"
  }
  ```

#### Alerts
- **Topic**: `sentinel/alerts`
- **QoS**: 1
- **Payload**:
  ```json
  {
    "level": "critical",
    "msg": "Intruder at door",
    "timestamp": "2024-12-17T10:30:20.123456"
  }
  ```

### Subscribed Topics

#### Commands
- **Topic**: `sentinel/commands`
- **Expected Payload**:
  ```json
  {
    "target": "door",
    "command": "UNLOCK"
  }
  ```

### Testing MQTT

Using `mosquitto_pub`:

```bash
# Send manual unlock command
mosquitto_pub -h localhost -t "sentinel/commands" \
  -m '{"target": "door", "command": "UNLOCK"}'
```

Using Python:

```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect("localhost", 1883, 60)

# Send unlock command
payload = {"target": "door", "command": "UNLOCK"}
client.publish("sentinel/commands", json.dumps(payload), qos=1)

client.disconnect()
```

## API Endpoints

### GET /video_feed
- **Description**: MJPEG video stream with face detection annotations
- **Content-Type**: `multipart/x-mixed-replace; boundary=frame`
- **Usage**: Embed in `<img>` tag or video player

Example HTML:
```html
<img src="http://localhost:5001/video_feed" alt="Door Camera" />
```

### GET /health
- **Description**: Service health check
- **Content-Type**: `application/json`
- **Response**:
  ```json
  {
    "status": "ok",
    "service": "door_sentry",
    "known_faces": 2
  }
  ```

## Troubleshooting

### Camera Not Found
```
Error: Failed to open camera
```
**Solution**: 
- Check camera is connected: `ls /dev/video*`
- Try different camera index in `.env`: `CAMERA_INDEX=1`
- Ensure camera permissions: `sudo usermod -a -G video $USER`

### MQTT Connection Failed
```
Warning: Continuing without MQTT - alerts and commands will not work
```
**Solution**:
- Start MQTT broker: `sudo systemctl start mosquitto`
- Check broker status: `mosquitto_sub -h localhost -t "#" -v`
- Verify broker settings in `.env`

### No Faces Recognized
**Solution**:
- Check face data exists in `data/authorized_faces/`
- Verify image quality (well-lit, clear face)
- Lower similarity threshold in code if needed
- Reload faces: restart the service

### High CPU Usage
**Solution**:
- Reduce camera resolution in code
- Decrease frame rate
- Use GPU acceleration if available (requires `onnxruntime-gpu`)

## Development

### Project Structure
```
Door_Sentry/
├── main.py              # Main service file
├── requirements.txt     # Service-specific dependencies
└── README.md           # This file
```

### Code Overview

**DoorSentry Class**:
- `__init__()`: Initialize camera, MQTT, FaceAuthenticator
- `process_frame()`: Main processing loop (face detection, authorization)
- `mqtt_callback()`: Handle incoming MQTT commands
- `generate_frames()`: Generator for Flask video streaming
- `cleanup()`: Clean shutdown

**Flask Routes**:
- `/video_feed`: MJPEG stream endpoint
- `/health`: Health check endpoint

### Extending Functionality

Add custom logic by modifying:
1. `process_frame()` - Add new face detection behaviors
2. `mqtt_callback()` - Handle new command types
3. `_publish_alert()` - Customize alert messages
4. Flask routes - Add new API endpoints

## Integration with Web Interface

The Web Interface can embed the video feed:

```html
<div class="camera-view">
  <h3>Front Door</h3>
  <img src="http://localhost:5001/video_feed" 
       alt="Door Camera" 
       style="width: 100%; max-width: 640px;" />
</div>

<button onclick="unlockDoor()">Unlock Door</button>

<script>
function unlockDoor() {
  // Send MQTT command via Web Interface backend
  fetch('/api/unlock-door', {method: 'POST'})
    .then(response => response.json())
    .then(data => console.log('Door unlocked:', data));
}
</script>
```

## Security Considerations

1. **Network Security**:
   - Use MQTT authentication (username/password)
   - Enable MQTT TLS for encrypted communication
   - Firewall rules to restrict access

2. **Face Recognition**:
   - Adjust `similarity_threshold` for security vs convenience
   - Regularly update face database
   - Consider multi-factor authentication for critical areas

3. **Video Privacy**:
   - Video feed should be on private network only
   - Consider adding authentication to Flask endpoints
   - No video recording by default (add if needed)

## License

Part of the Sentinel Security System project.
