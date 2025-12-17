# Sentinel Unified

A production-grade, unified security system with microservices architecture.

## 🏗️ Architecture

```
Sentinel_Unified/
├── Shared/                     # Core shared assets
│   ├── models/                 # YOLOv8 and InsightFace models
│   ├── data/
│   │   ├── authorized_faces/   # Single source of truth for face images
│   │   └── evidence/           # Shared storage for snapshots/videos
│   ├── libs/                   # Common Python modules
│   └── logs/                   # Centralized logging
├── Services/                   # Microservices
│   ├── Door_Sentry/            # Door monitoring (formerly Level_1)
│   ├── Interior_Watch/         # Interior surveillance (formerly Level_2)
│   └── Hardware_Sensors/       # Arduino/ESP32 code (formerly Level_3)
├── Web_Interface/              # Next.js dashboard
├── .env                        # Environment configuration
├── requirements.txt            # Python dependencies
└── start_sentinel.py           # Service orchestrator
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd Sentinel_Unified
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file with your specific configuration:
- MQTT broker settings
- Camera indices
- API keys and secrets

### 3. Start Services

```bash
# Start all services
python start_sentinel.py

# Or start a specific service
python start_sentinel.py --service door_sentry
```

## 📦 Technology Stack

- **Computer Vision**: YOLOv8 (Ultralytics), InsightFace
- **Backend**: Flask, Python 3.8+
- **Frontend**: Next.js, React, TypeScript
- **IoT**: MQTT, Arduino/ESP32
- **ML Runtime**: ONNX Runtime (GPU-accelerated)

## 🔒 Security Notes

- Change `SECRET_KEY` in `.env` before production deployment
- Use secure MQTT credentials
- Store face embeddings securely
- Review and update face recognition thresholds

## 📝 Migration Notes

This structure consolidates:
- **Level_1** → Services/Door_Sentry
- **Level_2** → Services/Interior_Watch  
- **Level_3** → Services/Hardware_Sensors
- **Web-Interface** → Web_Interface

All face datasets have been consolidated into `Shared/data/authorized_faces` as the single source of truth.

## 🛠️ Development

Each service is independently runnable for development:

```bash
# Door Sentry
cd Services/Door_Sentry
python run_system.py

# Interior Watch
cd Services/Interior_Watch
python theft_detection.py
```

## 📄 License

MIT License - See individual service directories for specific attributions.
