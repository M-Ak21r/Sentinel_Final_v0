# FaceAuthenticator Module

## Overview

`FaceAuthenticator` is a production-grade face authentication system for the Sentinel project. It serves as the single source of truth for identity verification across:
- **Door Sentry (Level 1)**: Decides whether to unlock the door
- **Interior Watch (Level 2)**: Distinguishes between authorized staff and potential intruders

## Features

### Core Capabilities
- **State-of-the-Art Recognition**: Uses InsightFace (ArcFace) with the 'buffalo_l' model
- **Automatic GPU/CPU Fallback**: Tries CUDA first, silently falls back to CPU
- **Smart Caching**: Fast boot with intelligent cache management
- **Centroid Embedding Strategy**: Creates robust "average" face embeddings for each person
- **Anatomical Filtering**: Quality control through size and aspect ratio checks
- **Cosine Similarity Matching**: Accurate face matching using normalized embeddings

### Production-Ready
- ✅ Comprehensive error handling
- ✅ Input validation
- ✅ Division by zero protection
- ✅ Detailed logging
- ✅ Zero security vulnerabilities (CodeQL verified)
- ✅ Type hints and docstrings

## Installation

### Dependencies
```bash
pip install insightface onnxruntime opencv-python numpy
```

Or install from the project requirements:
```bash
pip install -r Sentinel_Unified/requirements.txt
```

## Usage

### Basic Initialization

```python
from Sentinel_Unified.Shared.libs.face_auth import FaceAuthenticator

# Initialize with default settings
authenticator = FaceAuthenticator()

# Or customize parameters
authenticator = FaceAuthenticator(
    data_path="/path/to/authorized_faces",
    similarity_threshold=0.5,  # 0.0 to 1.0
    min_face_size=(30, 30)     # (width, height) in pixels
)
```

### Face Recognition

```python
import cv2

# Load image or capture from camera
frame = cv2.imread("image.jpg")

# Identify faces
results = authenticator.identify_face(frame)

# Process results
for person in results:
    print(f"Name: {person['name']}")
    print(f"Confidence: {person['confidence']:.2f}")
    print(f"Authorized: {person['is_authorized']}")
    print(f"Bounding Box: {person['bbox']}")
```

### Managing Known Faces

```python
# Get list of known faces
known_faces = authenticator.get_known_faces()
print(f"Known people: {known_faces}")

# Reload faces (e.g., after adding new photos)
authenticator.reload_faces()

# Get system statistics
stats = authenticator.get_stats()
print(f"Total known faces: {stats['num_known_faces']}")
```

## Directory Structure

The module expects the following structure:

```
data/authorized_faces/
├── John Doe/
│   ├── photo1.jpg
│   ├── photo2.jpg
│   └── photo3.png
├── Jane Smith/
│   ├── image1.jpg
│   └── image2.jpg
└── encodings.pkl  (auto-generated cache)
```

### Supported Image Formats
- `.jpg` / `.jpeg`
- `.png`
- `.bmp`

### Best Practices
- **Multiple Photos**: Use 3-10 photos per person for better accuracy
- **Variety**: Include different angles, lighting conditions, and expressions
- **Quality**: Use clear, well-lit photos with the face clearly visible
- **Single Face**: Each photo should contain only one person's face

## API Reference

### Constructor

```python
FaceAuthenticator(
    data_path: Optional[str] = None,
    similarity_threshold: float = 0.5,
    min_face_size: Tuple[int, int] = (30, 30)
)
```

**Parameters:**
- `data_path`: Path to authorized faces directory (default: `../../data/authorized_faces`)
- `similarity_threshold`: Minimum cosine similarity for match (0.0-1.0, default: 0.5)
- `min_face_size`: Minimum face dimensions in pixels (default: (30, 30))

### Methods

#### `identify_face(frame)`
Identify faces in a given frame.

**Parameters:**
- `frame`: CV2 image frame (numpy array) in BGR format

**Returns:**
List of dictionaries containing:
```python
{
    "name": str,           # Person's name or "Unknown"
    "confidence": float,   # Similarity score (0.0 to 1.0)
    "bbox": [int, int, int, int],  # [x1, y1, x2, y2]
    "is_authorized": bool, # True if confidence >= threshold
    "face_obj": object     # Raw InsightFace face object
}
```

#### `reload_faces()`
Force rebuild of face encodings cache.

Call this when:
- New faces are added to the authorized_faces directory
- Existing face images are updated or removed
- Web Interface triggers an update via MQTT

#### `get_known_faces()`
Returns list of all known (authorized) face names.

**Returns:** `List[str]`

#### `get_stats()`
Get system statistics.

**Returns:**
```python
{
    "num_known_faces": int,
    "known_faces": List[str],
    "data_path": str,
    "cache_exists": bool,
    "similarity_threshold": float,
    "min_face_size": Tuple[int, int]
}
```

## Integration Examples

### Door Sentry (Level 1)

```python
from Sentinel_Unified.Shared.libs.face_auth import FaceAuthenticator
import cv2

# Initialize
authenticator = FaceAuthenticator()

# Capture frame
cap = cv2.VideoCapture(0)
ret, frame = cap.read()

# Identify
results = authenticator.identify_face(frame)

# Check authorization
door_unlock = False
for person in results:
    if person['is_authorized']:
        print(f"Access granted for {person['name']}")
        door_unlock = True
        break

if door_unlock:
    # Trigger door unlock
    pass
```

### Interior Watch (Level 2)

```python
from Sentinel_Unified.Shared.libs.face_auth import FaceAuthenticator
import cv2

# Initialize
authenticator = FaceAuthenticator(similarity_threshold=0.6)

# Process video stream
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    results = authenticator.identify_face(frame)
    
    for person in results:
        if not person['is_authorized']:
            # Alert: Unknown person detected
            print(f"⚠️ ALERT: Unknown person at {person['bbox']}")
            # Trigger alarm, send notification, etc.
```

### MQTT Integration

```python
import paho.mqtt.client as mqtt
from Sentinel_Unified.Shared.libs.face_auth import FaceAuthenticator

authenticator = FaceAuthenticator()

def on_message(client, userdata, msg):
    if msg.topic == "sentinel/faces/reload":
        print("Reloading face database...")
        authenticator.reload_faces()
        print("Face database reloaded")

# Setup MQTT
client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("sentinel/faces/reload")
client.loop_start()
```

## Performance

### Cache System
- **First Boot**: Scans directory and builds embeddings (~5-10s for 10 people)
- **Subsequent Boots**: Loads from cache (~0.1s)
- **Cache Invalidation**: Automatic when directory is modified

### Recognition Speed
- **CPU Mode**: ~100-200ms per frame
- **GPU Mode**: ~20-50ms per frame (if CUDA available)

### Memory Usage
- **Base**: ~200MB (InsightFace model)
- **Per Person**: ~1KB (embedding storage)

## Troubleshooting

### "No module named 'insightface'"
```bash
pip install insightface onnxruntime
```

### GPU Not Available
The module automatically falls back to CPU. To enable GPU:
```bash
pip install onnxruntime-gpu
```

### Slow Recognition
- Use GPU if available
- Reduce frame resolution before processing
- Adjust `det_size` in the model (requires code modification)

### Low Accuracy
- Increase `similarity_threshold` (but not above 0.8)
- Add more training photos per person
- Ensure photos are high quality and well-lit

## Technical Details

### Centroid Embedding Strategy
Instead of storing individual face embeddings, the system:
1. Loads all photos for each person
2. Extracts face embeddings from each photo
3. Computes the mean (centroid) of all embeddings
4. Normalizes the resulting vector

This creates a stable "average" face that's more robust to lighting and angle variations.

### Cosine Similarity
Face matching uses the dot product of normalized embeddings:
```python
similarity = np.dot(embedding1, embedding2)
```

This ranges from -1.0 (opposite) to 1.0 (identical).

## License

Part of the Sentinel Unified project.

## Authors

- Sentinel Development Team
- Implemented as part of the Sentinel_Unified refactoring

## Version

1.0.0 - Initial production release
