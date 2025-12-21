"""
MongoDB Connection Manager
===========================
Thread-safe Singleton class for managing MongoDB connections across all Python microservices.

Author: Sentinel System
"""

import os
import logging
import threading
from pathlib import Path
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv


class MongoManager:
    """
    Thread-safe Singleton class for managing MongoDB connections.
    
    This class ensures only one MongoDB connection is created and shared
    across all microservices, providing efficient resource utilization.
    
    Usage:
        manager = MongoManager()
        db = manager.get_db()
        collection = manager.get_collection('users')
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """
        Thread-safe Singleton implementation.
        Ensures only one instance of MongoManager exists.
        """
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super(MongoManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the MongoDB connection manager.
        Only runs once due to Singleton pattern.
        """
        # Prevent re-initialization
        if self._initialized:
            return
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        # Load environment variables
        self._load_environment()
        
        # Initialize connection attributes
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        
        # Establish initial connection
        self._connect()
        
        # Mark as initialized
        self._initialized = True
    
    def _load_environment(self):
        """
        Load environment variables from .env file.
        The .env file is located 3 levels up from this file (at project root).
        """
        # Calculate path to .env file (3 levels up from this file)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        env_path = project_root / '.env'
        
        # Load .env file if it exists
        if env_path.exists():
            load_dotenv(env_path)
            self.logger.info(f"Loaded environment variables from: {env_path}")
        else:
            # Try .env.example as fallback
            env_example_path = project_root / '.env.example'
            if env_example_path.exists():
                load_dotenv(env_example_path)
                self.logger.warning(
                    f".env not found, using .env.example from: {env_example_path}"
                )
            else:
                self.logger.warning(
                    f"No .env file found at {env_path}. "
                    "Using system environment variables."
                )
        
        # Read MongoDB configuration with fallbacks
        self.mongodb_uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        self.mongodb_db = os.getenv('MONGODB_DB', 'security_dashboard')
        
        if not self.mongodb_uri:
            self.logger.error(
                "MONGODB_URI or MONGO_URI not found in environment variables!"
            )
            raise ValueError(
                "MONGODB_URI or MONGO_URI must be set in environment variables"
            )
        
        self.logger.info(f"MongoDB Database: {self.mongodb_db}")
    
    def _connect(self):
        """
        Establish connection to MongoDB with error handling.
        Uses serverSelectionTimeoutMS=5000 to fail fast if database is unreachable.
        """
        try:
            # Create MongoClient with fast timeout
            self.client = MongoClient(
                self.mongodb_uri,
                serverSelectionTimeoutMS=5000
            )
            
            # Force connection check
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[self.mongodb_db]
            
            self.logger.info(
                f"Successfully connected to MongoDB database: {self.mongodb_db}"
            )
            
        except ConnectionFailure as e:
            self.logger.error(
                f"Failed to connect to MongoDB: {e}. "
                "The database may be unreachable."
            )
            self.client = None
            self.db = None
        except Exception as e:
            self.logger.error(f"Unexpected error during MongoDB connection: {e}")
            self.client = None
            self.db = None
    
    def get_db(self):
        """
        Get the database object.
        Attempts to reconnect if the client is missing or connection is stale.
        
        Returns:
            Database object or None if connection failed.
        """
        # Check if we need to reconnect
        needs_reconnect = False
        
        if self.client is None or self.db is None:
            needs_reconnect = True
            self.logger.warning(
                "MongoDB client not connected. Attempting to reconnect..."
            )
        else:
            # Verify connection is still alive with a ping
            try:
                self.client.admin.command('ping')
            except Exception as e:
                needs_reconnect = True
                self.logger.warning(
                    f"MongoDB connection is stale: {e}. Attempting to reconnect..."
                )
        
        if needs_reconnect:
            self._connect()
        
        return self.db
    
    def get_collection(self, name: str):
        """
        Get a specific collection from the database.
        
        Args:
            name: Name of the collection to retrieve.
            
        Returns:
            Collection object or None if connection failed.
        """
        db = self.get_db()
        if db is not None:
            return db[name]
        else:
            self.logger.error(
                f"Cannot get collection '{name}': Database connection not available"
            )
            return None
