# MongoDB Connection Manager

## Overview

The `MongoManager` class provides a thread-safe, singleton-based MongoDB connection manager for all Python microservices in the Sentinel system.

## Features

- **Thread-Safe Singleton Pattern**: Ensures only one MongoDB connection is shared across all microservices
- **Auto-Reconnection**: Automatically attempts to reconnect if the connection is lost
- **Health Checking**: Verifies connection health with ping before operations
- **Graceful Error Handling**: Handles connection failures with comprehensive logging
- **Fast Timeout**: Uses `serverSelectionTimeoutMS=5000` to fail fast if database is unreachable

## Installation

The required dependency is already included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Configuration

Set the following environment variables in your `.env` file:

```bash
# MongoDB URI (either MONGODB_URI or MONGO_URI)
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/?appName=YourApp
# Or use MONGO_URI as fallback
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/?appName=YourApp

# Database name (defaults to 'security_dashboard')
MONGODB_DB=security_dashboard
```

## Usage

### Basic Usage

```python
from Sentinel_Unified.Shared.database import MongoManager

# Get the MongoDB manager instance
manager = MongoManager()

# Get the database
db = manager.get_db()

# Get a specific collection
users_collection = manager.get_collection('users')
alerts_collection = manager.get_collection('alerts')

# Use the collection
if users_collection:
    user = users_collection.find_one({'username': 'john_doe'})
    print(user)
```

### Example: Storing Security Alerts

```python
from Sentinel_Unified.Shared.database import MongoManager
from datetime import datetime

# Get manager instance
manager = MongoManager()

# Get alerts collection
alerts = manager.get_collection('alerts')

if alerts:
    # Insert a new alert
    alert_data = {
        'timestamp': datetime.utcnow(),
        'type': 'intrusion',
        'severity': 'high',
        'location': 'front_door',
        'details': 'Unauthorized person detected'
    }
    result = alerts.insert_one(alert_data)
    print(f"Alert inserted with ID: {result.inserted_id}")
    
    # Query recent alerts
    recent_alerts = alerts.find().sort('timestamp', -1).limit(10)
    for alert in recent_alerts:
        print(alert)
```

### Example: Face Recognition Data

```python
from Sentinel_Unified.Shared.database import MongoManager

manager = MongoManager()
faces_collection = manager.get_collection('authorized_faces')

if faces_collection:
    # Store authorized face data
    face_data = {
        'name': 'John Doe',
        'encoding': [0.1, 0.2, 0.3, ...],  # Face encoding array
        'registered_at': datetime.utcnow(),
        'access_level': 'admin'
    }
    faces_collection.insert_one(face_data)
    
    # Retrieve all authorized faces
    authorized_faces = list(faces_collection.find())
```

## Thread Safety

The `MongoManager` uses a thread-safe Singleton pattern with double-checked locking, ensuring that multiple threads can safely access the same MongoDB connection:

```python
import threading
from Sentinel_Unified.Shared.database import MongoManager

def worker():
    manager = MongoManager()
    collection = manager.get_collection('logs')
    # All threads will use the same MongoDB connection
    
threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

## Error Handling

The manager gracefully handles connection failures:

```python
manager = MongoManager()
db = manager.get_db()

if db is None:
    print("Database connection failed - check logs for details")
    # Your fallback logic here
else:
    # Normal database operations
    collection = db['my_collection']
```

## Logging

The manager uses Python's built-in logging module. Configure logging in your application:

```python
import logging

# Configure logging to see MongoDB connection status
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Architecture

```
Sentinel_Unified/
└── Shared/
    └── database/
        ├── __init__.py           # Exposes MongoManager
        └── mongo_manager.py      # Implementation
```

## Implementation Details

- **Singleton Pattern**: Uses `__new__` and `__init__` with a class-level lock
- **Environment Loading**: Automatically loads `.env` from project root (3 levels up)
- **Connection Timeout**: 5 seconds (`serverSelectionTimeoutMS=5000`)
- **Health Check**: Pings MongoDB before returning database object
- **Auto-Reconnect**: Attempts reconnection on stale or missing connections

## Notes

- The manager loads environment variables from `.env` file at the project root
- If `.env` is not found, it falls back to `.env.example`
- The database connection is lazy - it's established when MongoManager is first instantiated
- All microservices share the same MongoClient instance for efficiency
