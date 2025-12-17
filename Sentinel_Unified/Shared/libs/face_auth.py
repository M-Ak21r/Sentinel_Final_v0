"""
Face Authentication Module for Sentinel System
================================================
This module provides a robust, production-grade face authentication system
using InsightFace (ArcFace) for state-of-the-art face recognition.

Features:
- Automatic GPU/CPU fallback
- Centroid embedding strategy for robust recognition
- Fast boot with intelligent caching
- Comprehensive logging
- Anatomical filtering for quality control

Author: Sentinel System
"""

import os
import logging
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import cv2

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
        data_path (str): Path to authorized faces directory
        similarity_threshold (float): Minimum cosine similarity for match (0.0-1.0)
        min_face_size (tuple): Minimum face dimensions (width, height)
        app (FaceAnalysis): InsightFace application instance
        known_faces (dict): Dictionary mapping names to centroid embeddings
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
            data_path: Path to authorized faces directory. If None, defaults to
                      ../../data/authorized_faces relative to this file.
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
        
        # Resolve data path
        if data_path is None:
            # Default to ../../data/authorized_faces relative to this file
            current_file = Path(__file__).resolve()
            self.data_path = current_file.parent.parent.parent / "data" / "authorized_faces"
        else:
            self.data_path = Path(data_path)
        
        self.data_path = self.data_path.resolve()
        self.cache_file = self.data_path / "encodings.pkl"
        
        # Create data directory if it doesn't exist
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Initializing FaceAuthenticator")
        self.logger.info(f"Data path: {self.data_path}")
        self.logger.info(f"Similarity threshold: {similarity_threshold}")
        self.logger.info(f"Minimum face size: {min_face_size}")
        
        # Initialize InsightFace model
        self.app = self._initialize_model()
        
        # Dictionary to store known face embeddings {name: centroid_embedding}
        self.known_faces = {}
        
        # Load or build face encodings cache
        self._load_or_build_cache()
        
        self.logger.info(f"FaceAuthenticator initialized with {len(self.known_faces)} known faces")
    
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
    
    def _load_or_build_cache(self):
        """
        Load face encodings from cache or build new cache if needed.
        
        Cache is rebuilt if:
        - Cache file doesn't exist
        - Cache file is older than the data directory
        """
        should_rebuild = False
        
        if not self.cache_file.exists():
            self.logger.info("No cache file found, building new cache...")
            should_rebuild = True
        else:
            # Check if cache is outdated
            cache_mtime = self.cache_file.stat().st_mtime
            data_mtime = self.data_path.stat().st_mtime
            
            if data_mtime > cache_mtime:
                self.logger.info("Cache is outdated (data directory modified), rebuilding...")
                should_rebuild = True
            else:
                # Try to load cache
                try:
                    with open(self.cache_file, 'rb') as f:
                        self.known_faces = pickle.load(f)
                    self.logger.info(f"Loaded {len(self.known_faces)} faces from cache")
                    
                    # Validate cache data
                    if not isinstance(self.known_faces, dict):
                        self.logger.warning("Invalid cache format, rebuilding...")
                        should_rebuild = True
                except Exception as e:
                    self.logger.error(f"Error loading cache: {e}, rebuilding...")
                    should_rebuild = True
        
        if should_rebuild:
            self._build_cache()
    
    def _build_cache(self):
        """
        Build face encodings cache from authorized faces directory.
        
        This method:
        1. Scans subdirectories in data_path (each subdirectory = one person)
        2. Loads all valid images for each person
        3. Extracts face embeddings from each image
        4. Computes centroid (mean) embedding for each person
        5. Normalizes the centroid embeddings
        6. Saves the {name: centroid_embedding} map to cache file
        """
        self.logger.info("Building face encodings cache...")
        self.known_faces = {}
        
        if not self.data_path.exists():
            self.logger.warning(f"Data path does not exist: {self.data_path}")
            return
        
        # Iterate through person directories
        person_dirs = [d for d in self.data_path.iterdir() if d.is_dir()]
        
        if not person_dirs:
            self.logger.warning(f"No person directories found in {self.data_path}")
            return
        
        for person_dir in person_dirs:
            person_name = person_dir.name
            self.logger.info(f"Processing faces for: {person_name}")
            
            # Collect all embeddings for this person
            embeddings = []
            
            # Find all image files using class constant
            image_files = [
                f for f in person_dir.iterdir()
                if f.is_file() and f.suffix.lower() in self.VALID_IMAGE_EXTENSIONS
            ]
            
            if not image_files:
                self.logger.warning(f"No images found for {person_name}")
                continue
            
            for image_file in image_files:
                try:
                    # Load image
                    img = cv2.imread(str(image_file))
                    
                    if img is None:
                        self.logger.warning(f"Could not load image: {image_file}")
                        continue
                    
                    # Detect faces
                    faces = self.app.get(img)
                    
                    if not faces:
                        self.logger.warning(f"No face detected in: {image_file}")
                        continue
                    
                    # Use the first (and hopefully only) face
                    if len(faces) > 1:
                        self.logger.warning(
                            f"Multiple faces ({len(faces)}) detected in {image_file}, "
                            f"using first face only"
                        )
                    
                    face = faces[0]
                    embedding = face.embedding
                    
                    # Normalize embedding (check for zero norm)
                    embedding_norm = np.linalg.norm(embedding)
                    if embedding_norm > 0:
                        embedding = embedding / embedding_norm
                        embeddings.append(embedding)
                    else:
                        self.logger.warning(
                            f"Zero embedding norm in {image_file}, skipping"
                        )
                    
                except Exception as e:
                    self.logger.error(f"Error processing {image_file}: {e}")
                    continue
            
            if embeddings:
                # Compute centroid (mean) embedding
                centroid = np.mean(embeddings, axis=0)
                
                # Normalize the centroid (check for zero norm)
                centroid_norm = np.linalg.norm(centroid)
                if centroid_norm > 0:
                    centroid = centroid / centroid_norm
                    
                    self.known_faces[person_name] = centroid
                    self.logger.info(
                        f"Created centroid embedding for {person_name} "
                        f"from {len(embeddings)} images"
                    )
                else:
                    self.logger.warning(
                        f"Zero centroid norm for {person_name}, skipping"
                    )
            else:
                self.logger.warning(f"No valid embeddings extracted for {person_name}")
        
        # Save cache
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.known_faces, f)
            self.logger.info(f"Cache saved with {len(self.known_faces)} faces")
        except Exception as e:
            self.logger.error(f"Error saving cache: {e}")
    
    def reload_faces(self):
        """
        Force reload of face encodings by deleting cache and rebuilding.
        
        This method should be called when:
        - New faces are added to the authorized_faces directory
        - Existing face images are updated or removed
        - The system needs to refresh its recognition database
        
        This is typically triggered by the Web Interface via MQTT when
        a user uploads a new photo.
        """
        self.logger.info("Force reloading face encodings...")
        
        # Delete cache file if it exists
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
                self.logger.info("Cache file deleted")
            except Exception as e:
                self.logger.error(f"Error deleting cache file: {e}")
        
        # Rebuild cache
        self._build_cache()
        
        self.logger.info(f"Face encodings reloaded: {len(self.known_faces)} faces")
    
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
                
                if self.known_faces:
                    for name, known_embedding in self.known_faces.items():
                        # Calculate cosine similarity (dot product of normalized vectors)
                        similarity = np.dot(embedding, known_embedding)
                        
                        if similarity > best_confidence:
                            best_confidence = float(similarity)
                            best_name = name
                    
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
        return list(self.known_faces.keys())
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the face authentication system.
        
        Returns:
            Dictionary containing system statistics
        """
        return {
            "num_known_faces": len(self.known_faces),
            "known_faces": self.get_known_faces(),
            "data_path": str(self.data_path),
            "cache_exists": self.cache_file.exists(),
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
    print(f"  Data path: {stats['data_path']}")
    print(f"  Cache exists: {stats['cache_exists']}")
    print(f"  Similarity threshold: {stats['similarity_threshold']}")
    print(f"  Min face size: {stats['min_face_size']}")
    
    print("\n" + "="*60)
    print("FaceAuthenticator initialized successfully!")
    print("="*60)
