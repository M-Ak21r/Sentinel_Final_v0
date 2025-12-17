#!/usr/bin/env python3
"""
Sentinel Unified - Project Setup Script
========================================
This script restructures the Sentinel security system from disparate modules
(Level_1, Level_2, Level_3, Web-Interface) into a unified, production-grade
architecture with proper separation of concerns.

Author: Sentinel Team
License: MIT
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple


class SentinelProjectSetup:
    """Orchestrates the migration to Sentinel_Unified architecture."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
        self.sentinel_unified = self.base_path / "Sentinel_Unified"
        
        # Define the target directory structure
        self.directories = [
            # Shared resources
            "Shared/models",
            "Shared/data/authorized_faces",
            "Shared/data/evidence",
            "Shared/libs",
            "Shared/logs",
            # Services (formerly Levels)
            "Services/Door_Sentry",
            "Services/Interior_Watch",
            "Services/Hardware_Sensors",
            # Web Interface
            "Web_Interface",
        ]
        
        # Define migration mappings: (source, destination)
        self.migrations = [
            ("Level_1", "Services/Door_Sentry"),
            ("Level_2", "Services/Interior_Watch"),
            ("Level_3", "Services/Hardware_Sensors"),
            ("Web-Interface", "Web_Interface"),
        ]
        
        # Assets to consolidate
        self.face_dataset_sources = [
            "Level_1/faces_dataset",
            "Level_2/authorized_personnel",
        ]
        
        self.model_patterns = ["*.pt", "*.onnx", "*.yml"]
        
    def log(self, message: str, level: str = "INFO"):
        """Print formatted log messages."""
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
        }.get(level, "  ")
        print(f"{prefix} {message}")
    
    def create_directory_structure(self):
        """Create the Sentinel_Unified directory tree."""
        self.log("Creating Sentinel_Unified directory structure...")
        
        if self.sentinel_unified.exists():
            self.log(f"Directory '{self.sentinel_unified}' already exists!", "WARNING")
            response = input("Do you want to remove it and start fresh? (yes/no): ")
            if response.lower() in ["yes", "y"]:
                shutil.rmtree(self.sentinel_unified)
                self.log("Removed existing directory", "INFO")
            else:
                self.log("Aborting setup to avoid data loss", "ERROR")
                sys.exit(1)
        
        # Create all directories
        for directory in self.directories:
            dir_path = self.sentinel_unified / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            self.log(f"Created: {directory}", "SUCCESS")
    
    def migrate_service_directories(self):
        """Move Level_X and Web-Interface contents to Services."""
        self.log("\nMigrating service directories...")
        
        for source, destination in self.migrations:
            source_path = self.base_path / source
            dest_path = self.sentinel_unified / destination
            
            if not source_path.exists():
                self.log(f"Source '{source}' not found, skipping", "WARNING")
                continue
            
            self.log(f"Migrating {source} → {destination}...")
            
            # Copy all contents
            if dest_path.exists():
                # Destination already exists (created in structure phase)
                for item in source_path.iterdir():
                    if item.name.startswith('.'):
                        continue  # Skip hidden files
                    
                    dest_item = dest_path / item.name
                    
                    if item.is_dir():
                        if dest_item.exists():
                            shutil.rmtree(dest_item)
                        shutil.copytree(item, dest_item)
                    else:
                        shutil.copy2(item, dest_item)
                
                self.log(f"  Copied contents of {source}", "SUCCESS")
            else:
                self.log(f"  Destination {destination} doesn't exist!", "ERROR")
    
    def consolidate_face_datasets(self):
        """Consolidate face datasets into single source of truth."""
        self.log("\nConsolidating face datasets...")
        
        target_dir = self.sentinel_unified / "Shared/data/authorized_faces"
        
        for source in self.face_dataset_sources:
            source_path = self.base_path / source
            
            # Also check in the migrated Services directories
            if not source_path.exists():
                # Check in Services after migration
                if "Level_1" in source:
                    source_path = self.sentinel_unified / "Services/Door_Sentry/faces_dataset"
                elif "Level_2" in source:
                    source_path = self.sentinel_unified / "Services/Interior_Watch/authorized_personnel"
            
            if not source_path.exists():
                self.log(f"Face dataset '{source}' not found, skipping", "WARNING")
                continue
            
            self.log(f"Consolidating faces from {source_path.name}...")
            
            # Copy all image files
            copied_count = 0
            for item in source_path.rglob("*"):
                if item.is_file() and item.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                    # Create subdirectory structure if needed
                    relative_path = item.relative_to(source_path)
                    dest_file = target_dir / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(item, dest_file)
                    copied_count += 1
            
            self.log(f"  Copied {copied_count} face images", "SUCCESS")
    
    def consolidate_models(self):
        """Move model files to Shared/models."""
        self.log("\nConsolidating model files...")
        
        target_dir = self.sentinel_unified / "Shared/models"
        model_files_found = []
        
        # Search in original directories first
        for source_dir in ["Level_1", "Level_2"]:
            source_path = self.base_path / source_dir
            if source_path.exists():
                for pattern in self.model_patterns:
                    model_files_found.extend(source_path.glob(pattern))
        
        # Also search in migrated Services directories
        services_dir = self.sentinel_unified / "Services"
        if services_dir.exists():
            for pattern in self.model_patterns:
                model_files_found.extend(services_dir.rglob(pattern))
        
        if not model_files_found:
            self.log("No model files (.pt, .onnx, .yml) found", "WARNING")
            return
        
        copied_count = 0
        for model_file in model_files_found:
            dest_file = target_dir / model_file.name
            
            # Avoid duplicates
            if dest_file.exists():
                continue
            
            shutil.copy2(model_file, dest_file)
            self.log(f"  Moved: {model_file.name}", "SUCCESS")
            copied_count += 1
        
        self.log(f"Consolidated {copied_count} model files", "SUCCESS")
    
    def create_unified_requirements(self):
        """Generate unified requirements.txt with Level 2's tech stack."""
        self.log("\nCreating unified requirements.txt...")
        
        requirements_content = """# Sentinel Unified - Python Dependencies
# ========================================
# Core Vision & AI
ultralytics>=8.0.0
insightface>=0.7.3
onnxruntime-gpu>=1.16.0
opencv-python>=4.8.0
numpy>=1.24.0

# Web Framework
flask>=2.3.0
flask-cors>=4.0.0

# IoT & Messaging
paho-mqtt>=1.6.0

# Configuration & Environment
python-dotenv>=1.0.0

# Utilities
requests>=2.31.0
"""
        
        requirements_path = self.sentinel_unified / "requirements.txt"
        requirements_path.write_text(requirements_content)
        self.log("Created requirements.txt", "SUCCESS")
    
    def create_env_template(self):
        """Generate .env template with secure defaults."""
        self.log("\nCreating .env configuration template...")
        
        env_content = """# Sentinel Unified - Environment Configuration
# ==============================================

# MQTT Broker Settings
MQTT_BROKER_URL=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# Camera Configuration
DOOR_CAMERA_INDEX=0
INTERIOR_CAMERA_INDEX=1

# Shared Data Paths
SHARED_DATA_PATH=./Shared/data
SHARED_MODELS_PATH=./Shared/models
SHARED_LOGS_PATH=./Shared/logs

# Flask Security
SECRET_KEY=change-this-to-a-random-secure-key-in-production

# Service Ports
DOOR_SENTRY_PORT=5001
INTERIOR_WATCH_PORT=5002
WEB_INTERFACE_PORT=3000

# Logging Configuration
LOG_LEVEL=INFO
LOG_TO_FILE=true

# Face Recognition Thresholds
FACE_CONFIDENCE_THRESHOLD=0.85
YOLO_CONFIDENCE_THRESHOLD=0.5

# Alert Settings
ENABLE_EMAIL_ALERTS=false
ENABLE_SMS_ALERTS=false
ALERT_EMAIL=
"""
        
        env_path = self.sentinel_unified / ".env"
        env_path.write_text(env_content)
        self.log("Created .env template", "SUCCESS")
    
    def create_orchestration_script(self):
        """Create placeholder orchestration script."""
        self.log("\nCreating orchestration script...")
        
        orchestration_content = """#!/usr/bin/env python3
\"\"\"
Sentinel Unified - Service Orchestrator
========================================
This script starts and manages all Sentinel microservices.

Usage:
    python start_sentinel.py [--service SERVICE_NAME]
    
Options:
    --service    Start a specific service only (door_sentry, interior_watch, web)
    --all        Start all services (default)
\"\"\"

import argparse
import os
import subprocess
import sys
from pathlib import Path


def load_env():
    \"\"\"Load environment variables from .env file.\"\"\"
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            print("✅ Environment variables loaded")
        else:
            print("⚠️  .env file not found, using defaults")
    except ImportError:
        print("⚠️  python-dotenv not installed, skipping .env loading")


def start_service(service_name: str):
    \"\"\"Start a specific Sentinel service.\"\"\"
    services = {
        "door_sentry": "Services/Door_Sentry",
        "interior_watch": "Services/Interior_Watch",
        "web": "Web_Interface",
    }
    
    if service_name not in services:
        print(f"❌ Unknown service: {service_name}")
        print(f"Available services: {', '.join(services.keys())}")
        return False
    
    service_path = Path(__file__).parent / services[service_name]
    
    if not service_path.exists():
        print(f"❌ Service directory not found: {service_path}")
        return False
    
    print(f"🚀 Starting {service_name}...")
    # TODO: Implement actual service startup logic
    print(f"   Service path: {service_path}")
    print(f"   (Implementation pending)")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Sentinel Unified Service Orchestrator")
    parser.add_argument(
        "--service",
        choices=["door_sentry", "interior_watch", "web", "all"],
        default="all",
        help="Service to start (default: all)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🛡️  SENTINEL UNIFIED - Service Orchestrator")
    print("=" * 60)
    
    load_env()
    
    if args.service == "all":
        print("\\n🚀 Starting all services...")
        start_service("door_sentry")
        start_service("interior_watch")
        start_service("web")
    else:
        start_service(args.service)
    
    print("\\n" + "=" * 60)
    print("✅ Orchestrator setup complete")
    print("⚠️  Note: Service startup logic needs to be implemented")
    print("=" * 60)


if __name__ == "__main__":
    main()
"""
        
        orchestration_path = self.sentinel_unified / "start_sentinel.py"
        orchestration_path.write_text(orchestration_content)
        
        # Make it executable
        orchestration_path.chmod(0o755)
        
        self.log("Created start_sentinel.py", "SUCCESS")
    
    def create_readme(self):
        """Create README for the new structure."""
        self.log("\nCreating README...")
        
        readme_content = """# Sentinel Unified

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
"""
        
        readme_path = self.sentinel_unified / "README.md"
        readme_path.write_text(readme_content)
        self.log("Created README.md", "SUCCESS")
    
    def run(self):
        """Execute the complete setup process."""
        print("\n" + "=" * 70)
        print("🛡️  SENTINEL UNIFIED - Project Setup")
        print("=" * 70)
        print("\nThis script will restructure your project into a unified architecture.")
        print(f"Base directory: {self.base_path}")
        print(f"Target directory: {self.sentinel_unified}")
        print("\n" + "=" * 70 + "\n")
        
        try:
            # Execute migration steps
            self.create_directory_structure()
            self.migrate_service_directories()
            self.consolidate_face_datasets()
            self.consolidate_models()
            self.create_unified_requirements()
            self.create_env_template()
            self.create_orchestration_script()
            self.create_readme()
            
            # Success summary
            print("\n" + "=" * 70)
            print("✅ SETUP COMPLETE!")
            print("=" * 70)
            self.log("\nYour Sentinel system has been restructured successfully!", "SUCCESS")
            self.log(f"New structure located at: {self.sentinel_unified}", "INFO")
            print("\n📋 Next Steps:")
            print("  1. cd Sentinel_Unified")
            print("  2. pip install -r requirements.txt")
            print("  3. Edit .env with your configuration")
            print("  4. python start_sentinel.py")
            print("\n" + "=" * 70 + "\n")
            
        except Exception as e:
            self.log(f"Setup failed: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Entry point for the setup script."""
    # Allow running from any directory
    script_dir = Path(__file__).parent
    setup = SentinelProjectSetup(base_path=script_dir)
    setup.run()


if __name__ == "__main__":
    main()
