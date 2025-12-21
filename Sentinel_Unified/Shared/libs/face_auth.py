"""
Face Authentication Module for Sentinel System
================================================
This module provides a robust, production-grade face authentication system
using InsightFace (ArcFace) for state-of-the-art face recognition.

Features:
- Automatic GPU/CPU fallback
- MongoDB-based face storage
- Fast boot with intelligent caching
- Comprehensive logging
- Anatomical filtering for quality control

Author: Sentinel System
"""

import sys
import os
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import cv2
from datetime import datetime

# Add Shared directory to path for imports
current_file = Path(__file__).resolve()
shared_dir = current_file.parent.parent
if str(shared_dir) not in sys.path:
    sys.path.insert(0, str(shared_dir))

from database.mongo_manager import MongoManager

try:
    from insightface.app import FaceAnalysis
except ImportError:
    raise ImportError(
        "insightface is required. Install with: pip install insightface"
    )


class FaceAuthenticator:
    """
    Production-grade face authentication system using InsightFace ArcFace.
    
    This class serves as the single source of truth for identity verification
    across the Sentinel system (Door Sentry and Interior Watch).
    
    Attributes:
        similarity_threshold (float): Minimum cosine similarity for match (0.0-1.0)
        min_face_size (tuple): Minimum face dimensions (width, height)
        app (FaceAnalysis): InsightFace application instance
        known_face_encodings (list): List of face embeddings (numpy arrays)
        known_face_names (list): List of corresponding names
        mongo (MongoManager): MongoDB connection manager
        logger (logging.Logger): Logger instance
    """
    
    # Supported image file extensions
    VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    def __init__(
        self,
        data_path: Optional[str] = None,
        similarity_threshold: float = 0.5,
        min_face_size: Tuple[int, int] = (30, 30)
    ):
        """
        Initialize the FaceAuthenticator.
        
        Args:
            data_path: (Deprecated, kept for backward compatibility) 
                      Path to authorized faces directory. No longer used.
            similarity_threshold: Minimum cosine similarity score (0.0-1.0) for
                                a face to be considered a match. Default: 0.5
            min_face_size: Minimum face dimensions (width, height) in pixels.
                          Faces smaller than this are ignored. Default: (30, 30)
        """
        # Setup logging
        self.logger = self._setup_logging()
        
        # Store configuration
        self.similarity_threshold = similarity_threshold
        self.min_face_size = min_face_size
        
        self.logger.info(f"Initializing FaceAuthenticator")
        self.logger.info(f"Similarity threshold: {similarity_threshold}")
        self.logger.info(f"Minimum face size: {min_face_size}")
        
        # Initialize MongoDB connection
        self.mongo = MongoManager()
        self.logger.info("MongoDB connection initialized")
        
        # Initialize InsightFace model
        self.app = self._initialize_model()
        
        # Lists to store known face encodings and names
        self.known_face_encodings = []
        self.known_face_names = []
        
        # Load face encodings from database
        self.load_faces_from_db()
        
        self.logger.info(f"FaceAuthenticator initialized with {len(self.known_face_names)} known faces")
    
    def _setup_logging(self) -> logging.Logger:
        """
        Setup logging configuration.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        logger = logging.getLogger(__name__)
        
        # Only add handlers if they don't exist (avoid duplicate logs)
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Format
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
        
        return logger
    
    def _initialize_model(self) -> FaceAnalysis:
        """
        Initialize the InsightFace FaceAnalysis model with automatic GPU/CPU fallback.
        
        Returns:
            FaceAnalysis: Initialized face analysis application
        
        Raises:
            RuntimeError: If model initialization fails
        """
        self.logger.info("Initializing InsightFace model (buffalo_l)...")
        
        # Try GPU first, then fallback to CPU
        providers = []
        try:
            import onnxruntime as ort
            available_providers = ort.get_available_providers()
            
            if 'CUDAExecutionProvider' in available_providers:
                providers.append('CUDAExecutionProvider')
                self.logger.info("GPU acceleration available - using CUDAExecutionProvider")
            else:
                self.logger.info("GPU not available - using CPU")
        except Exception as e:
            self.logger.warning(f"Could not check for GPU: {e}")
        
        # Always add CPU as fallback
        providers.append('CPUExecutionProvider')
        
        try:
            app = FaceAnalysis(
                name='buffalo_l',
                providers=providers
            )
            app.prepare(ctx_id=0, det_size=(640, 640))
            
            self.logger.info(f"InsightFace model initialized successfully with providers: {providers}")
            return app
            
        except Exception as e:
            # If GPU fails, try CPU only
            if len(providers) > 1:
                self.logger.warning(f"Failed with GPU, falling back to CPU only: {e}")
                try:
                    app = FaceAnalysis(
                        name='buffalo_l',
                        providers=['CPUExecutionProvider']
                    )
                    app.prepare(ctx_id=-1, det_size=(640, 640))
                    self.logger.info("InsightFace model initialized successfully with CPU")
                    return app
                except Exception as e2:
                    raise RuntimeError(f"Failed to initialize face recognition model: {e2}")
            else:
                raise RuntimeError(f"Failed to initialize face recognition model: {e}")
    
    def load_faces_from_db(self):
        """
        Load face encodings from MongoDB database.
        
        This method:
        1. Retrieves all documents from the 'authorized_faces' collection
        2. Extracts name and embedding from each document
        3. Converts embeddings from list to numpy array
        4. Stores them in the local cache (known_face_encodings and known_face_names)
        """
        self.logger.info("Loading face encodings from MongoDB...")
        
        # Clear existing data
        self.known_face_encodings = []
        self.known_face_names = []
        
        try:
            # Get the authorized_faces collection
            collection = self.mongo.get_collection('authorized_faces')
            
            if collection is None:
                self.logger.error("Failed to get authorized_faces collection")
                return
            
            # Iterate through all documents
            for doc in collection.find({"active": True}):
                try:
                    name = doc.get('name')
                    embedding_list = doc.get('embedding')
                    
                    if name is None or embedding_list is None:
                        self.logger.warning(f"Skipping document with missing name or embedding: {doc.get('_id')}")
                        continue
                    
                    # Validate embedding structure (should be 512D list from InsightFace)
                    if not isinstance(embedding_list, list) or len(embedding_list) != 512:
                        self.logger.warning(
                            f"Skipping document {doc.get('_id')}: Invalid embedding "
                            f"(expected list of 512 floats, got {type(embedding_list)} "
                            f"with length {len(embedding_list) if isinstance(embedding_list, list) else 'N/A'})"
                        )
                        continue
                    
                    # Convert embedding from list to numpy array
                    embedding = np.array(embedding_list, dtype=np.float32)
                    
                    # Store in local cache
                    self.known_face_encodings.append(embedding)
                    self.known_face_names.append(name)
                    
                except Exception as e:
                    self.logger.error(f"Error processing document {doc.get('_id')}: {e}")
                    continue
            
            self.logger.info(f"Loaded {len(self.known_face_names)} faces from MongoDB")
            
        except Exception as e:
            self.logger.error(f"Error loading faces from MongoDB: {e}")
    
    def register_face(self, name: str, image: np.ndarray) -> bool:
        """
        Register a new face in the database.
        
        This is a NEW method to register a face programmatically.
        
        Args:
            name: Name of the person to register
            image: CV2 image containing the face (numpy array in BGR format)
            
        Returns:
            True if face was successfully registered, False otherwise
        """
        self.logger.info(f"Registering face for: {name}")
        
        try:
            # Get face embedding from the image
            embedding = self.get_face_embedding(image)
            
            if embedding is None:
                self.logger.warning(f"No face detected in image for {name}")
                return False
            
            # Create document for MongoDB
            # Note: InsightFace ArcFace produces 512-dimensional float32 embeddings
            doc = {
                "name": name,
                "embedding": embedding.tolist(),  # Convert numpy to list for MongoDB
                "created_at": datetime.now(),
                "active": True
            }
            
            # Insert into authorized_faces collection
            collection = self.mongo.get_collection('authorized_faces')
            
            if collection is None:
                self.logger.error("Failed to get authorized_faces collection")
                return False
            
            result = collection.insert_one(doc)
            
            # Verify insert succeeded before updating local cache
            if result and result.inserted_id:
                # Update local cache
                self.known_face_encodings.append(embedding)
                self.known_face_names.append(name)
                
                self.logger.info(f"Successfully registered face for {name} with ID: {result.inserted_id}")
                return True
            else:
                self.logger.error(f"Failed to insert document for {name}: No inserted_id returned")
                return False
            
        except Exception as e:
            self.logger.error(f"Error registering face for {name}: {e}")
            return False
    
    def get_face_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract face embedding from an image.
        
        Args:
            image: CV2 image containing a face (numpy array in BGR format)
            
        Returns:
            Normalized face embedding as numpy array, or None if no face detected
        """
        try:
            # Detect faces in the image
            faces = self.app.get(image)
            
            if not faces:
                self.logger.debug("No face detected in image")
                return None
            
            if len(faces) > 1:
                self.logger.warning(f"Multiple faces ({len(faces)}) detected, using first face only")
            
            # Use the first face
            face = faces[0]
            embedding = face.embedding
            
            # Normalize embedding
            embedding_norm = np.linalg.norm(embedding)
            if embedding_norm > 0:
                embedding = embedding / embedding_norm
                return embedding
            else:
                self.logger.warning("Detected face has zero embedding norm")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting face embedding: {e}")
            return None
    
    def reload_faces(self):
        """
        Force reload of face encodings from MongoDB.
        
        This method should be called when:
        - New faces are added to the database
        - Existing face records are updated or removed
        - The system needs to refresh its recognition database
        
        This is typically triggered by the Web Interface via MQTT when
        a user uploads a new photo.
        """
        self.logger.info("Force reloading face encodings from MongoDB...")
        self.load_faces_from_db()
        self.logger.info(f"Face encodings reloaded: {len(self.known_face_names)} faces")
    
    def identify_face(self, frame: np.ndarray) -> List[Dict]:
        """
        Identify faces in the given frame.
        
        Args:
            frame: CV2 image frame (numpy array) in BGR format
        
        Returns:
            List of dictionaries, one per detected face, containing:
            - name (str): Person's name if authorized, "Unknown" otherwise
            - confidence (float): Similarity score (0.0 to 1.0)
            - bbox (list): Bounding box [x1, y1, x2, y2] as integers
            - is_authorized (bool): True if face matches a known person
            - face_obj (object): Raw InsightFace face object (optional)
        
        Example:
            >>> authenticator = FaceAuthenticator()
            >>> frame = cv2.imread("image.jpg")
            >>> results = authenticator.identify_face(frame)
            >>> for result in results:
            ...     print(f"{result['name']}: {result['confidence']:.2f}")
        """
        results = []
        
        # Input validation
        if frame is None or frame.size == 0:
            self.logger.warning("Empty or malformed frame received")
            return results
        
        try:
            # Detect faces
            faces = self.app.get(frame)
            
            if not faces:
                self.logger.debug("No faces detected in frame")
                return results
            
            self.logger.debug(f"Detected {len(faces)} face(s)")
            
            # Process each detected face
            for face in faces:
                # Extract bounding box
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox
                
                # Anatomical filtering: Check face size and aspect ratio
                face_width = x2 - x1
                face_height = y2 - y1
                
                # Check for invalid dimensions early
                if face_height <= 0 or face_width <= 0:
                    self.logger.debug(
                        f"Ignoring face with invalid dimensions: {face_width}x{face_height}"
                    )
                    continue
                
                if face_width < self.min_face_size[0] or face_height < self.min_face_size[1]:
                    self.logger.debug(
                        f"Ignoring small face: {face_width}x{face_height} "
                        f"(min: {self.min_face_size})"
                    )
                    continue
                
                # Anatomical filtering: Check aspect ratio (optional)
                aspect_ratio = face_width / face_height
                if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                    self.logger.debug(
                        f"Ignoring face with extreme aspect ratio: {aspect_ratio:.2f}"
                    )
                    continue
                
                # Extract and normalize embedding
                embedding = face.embedding
                
                # Normalize embedding (check for zero norm)
                embedding_norm = np.linalg.norm(embedding)
                if embedding_norm > 0:
                    embedding = embedding / embedding_norm
                else:
                    self.logger.warning("Detected face has zero embedding norm, skipping")
                    continue
                
                # Find best match
                best_name = "Unknown"
                best_confidence = 0.0
                is_authorized = False
                
                if self.known_face_encodings:
                    for i, known_embedding in enumerate(self.known_face_encodings):
                        # Calculate cosine similarity (dot product of normalized vectors)
                        similarity = np.dot(embedding, known_embedding)
                        
                        if similarity > best_confidence:
                            best_confidence = float(similarity)
                            best_name = self.known_face_names[i]
                    
                    # Check if confidence exceeds threshold
                    if best_confidence >= self.similarity_threshold:
                        is_authorized = True
                    else:
                        best_name = "Unknown"
                        is_authorized = False
                
                # Create result dictionary
                result = {
                    "name": best_name,
                    "confidence": best_confidence,
                    "bbox": [x1, y1, x2, y2],
                    "is_authorized": is_authorized,
                    "face_obj": face  # Include raw face object for advanced use
                }
                
                results.append(result)
                
                self.logger.debug(
                    f"Face identified: {best_name} "
                    f"(confidence: {best_confidence:.3f}, "
                    f"authorized: {is_authorized})"
                )
            
        except Exception as e:
            self.logger.error(f"Error during face identification: {e}", exc_info=True)
        
        return results
    
    def get_known_faces(self) -> List[str]:
        """
        Get list of all known (authorized) face names.
        
        Returns:
            List of person names that are registered in the system
        """
        return list(self.known_face_names)
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the face authentication system.
        
        Returns:
            Dictionary containing system statistics
        """
        return {
            "num_known_faces": len(self.known_face_names),
            "known_faces": self.get_known_faces(),
            "similarity_threshold": self.similarity_threshold,
            "min_face_size": self.min_face_size
        }


# Example usage
if __name__ == "__main__":
    # Setup basic logging for demo
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*60)
    print("FaceAuthenticator Demo")
    print("="*60)
    
    # Initialize authenticator
    authenticator = FaceAuthenticator(
        similarity_threshold=0.5,
        min_face_size=(30, 30)
    )
    
    # Display stats
    stats = authenticator.get_stats()
    print("\nSystem Statistics:")
    print(f"  Known faces: {stats['num_known_faces']}")
    print(f"  Names: {stats['known_faces']}")
    print(f"  Similarity threshold: {stats['similarity_threshold']}")
    print(f"  Min face size: {stats['min_face_size']}")
    
    print("\n" + "="*60)
    print("FaceAuthenticator initialized successfully!")
    print("="*60)
