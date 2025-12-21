"""
File Utilities Module
=====================
Cross-platform file locking, atomic writes, and verification utilities
to prevent file corruption in concurrent environments.

Author: Sentinel System
"""

import os
import sys
import json
import csv
import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

# Platform-specific imports for file locking
if sys.platform == 'win32':
    import msvcrt
else:
    import fcntl


class FileLock:
    """
    Cross-platform file locking mechanism.
    
    Usage:
        with FileLock('/path/to/file.lock'):
            # Critical section - file operations
            pass
    """
    
    def __init__(self, lock_file: str, timeout: float = 10.0):
        """
        Initialize file lock.
        
        Args:
            lock_file: Path to lock file
            timeout: Maximum time to wait for lock (seconds)
        """
        self.lock_file = Path(lock_file)
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.file_handle = None
    
    def __enter__(self):
        """Acquire lock."""
        import time
        
        start_time = time.time()
        
        while True:
            try:
                # Open/create lock file
                self.file_handle = open(self.lock_file, 'w')
                
                # Try to acquire lock
                if sys.platform == 'win32':
                    # Windows: Lock first byte
                    msvcrt.locking(
                        self.file_handle.fileno(),
                        msvcrt.LK_NBLCK,
                        1
                    )
                else:
                    # Linux/Unix: Exclusive lock
                    fcntl.flock(
                        self.file_handle.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                
                # Lock acquired successfully
                return self
                
            except (IOError, OSError) as e:
                # Lock is held by another process
                if self.file_handle:
                    self.file_handle.close()
                    self.file_handle = None
                
                # Check timeout
                if time.time() - start_time >= self.timeout:
                    raise TimeoutError(
                        f"Could not acquire lock on {self.lock_file} "
                        f"within {self.timeout} seconds"
                    )
                
                # Wait before retry
                time.sleep(0.1)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release lock."""
        if self.file_handle:
            try:
                # Release lock
                if sys.platform == 'win32':
                    msvcrt.locking(
                        self.file_handle.fileno(),
                        msvcrt.LK_UNLCK,
                        1
                    )
                else:
                    fcntl.flock(
                        self.file_handle.fileno(),
                        fcntl.LOCK_UN
                    )
            except Exception:
                pass
            finally:
                self.file_handle.close()
                self.file_handle = None


def atomic_write_text(file_path: str, content: str, encoding: str = 'utf-8') -> bool:
    """
    Write text file atomically using temp file + rename pattern.
    
    Args:
        file_path: Target file path
        content: Text content to write
        encoding: Text encoding (default: utf-8)
    
    Returns:
        bool: True if successful, False otherwise
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create lock file path
    lock_file = file_path.parent / f".{file_path.name}.lock"
    
    try:
        with FileLock(str(lock_file)):
            # Write to temporary file in same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(file_path.parent),
                prefix=f".{file_path.name}.tmp"
            )
            
            try:
                with os.fdopen(temp_fd, 'w', encoding=encoding) as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                
                # Atomic rename
                shutil.move(temp_path, str(file_path))
                return True
                
            except Exception as e:
                # Cleanup temp file on error
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise e
                
    except Exception as e:
        print(f"Error in atomic_write_text({file_path}): {e}")
        return False


def atomic_write_json(file_path: str, data: Any, indent: int = 2) -> bool:
    """
    Write JSON file atomically with file locking.
    
    Args:
        file_path: Target JSON file path
        data: Data to serialize as JSON
        indent: JSON indentation (default: 2)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        json_str = json.dumps(data, indent=indent)
        return atomic_write_text(file_path, json_str)
    except Exception as e:
        print(f"Error in atomic_write_json({file_path}): {e}")
        return False


def atomic_append_csv(file_path: str, row: List[Any], 
                      create_if_missing: bool = True,
                      header: Optional[List[str]] = None) -> bool:
    """
    Append row to CSV file atomically with file locking.
    
    Args:
        file_path: Target CSV file path
        row: Row data as list
        create_if_missing: Create file if it doesn't exist
        header: Header row (used only when creating new file)
    
    Returns:
        bool: True if successful, False otherwise
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create lock file path
    lock_file = file_path.parent / f".{file_path.name}.lock"
    
    try:
        with FileLock(str(lock_file)):
            # Check if file exists
            file_exists = file_path.exists()
            
            if not file_exists and not create_if_missing:
                return False
            
            # Open in append mode
            with open(file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header if creating new file
                if not file_exists and header:
                    writer.writerow(header)
                
                # Write data row
                writer.writerow(row)
                f.flush()
                os.fsync(f.fileno())
            
            return True
            
    except Exception as e:
        print(f"Error in atomic_append_csv({file_path}): {e}")
        return False


def safe_read_json(file_path: str, default: Any = None) -> Any:
    """
    Safely read JSON file with file locking and error handling.
    
    Args:
        file_path: JSON file path
        default: Default value if file doesn't exist or is corrupted
    
    Returns:
        Parsed JSON data or default value
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return default
    
    # Create lock file path
    lock_file = file_path.parent / f".{file_path.name}.lock"
    
    try:
        with FileLock(str(lock_file)):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error reading JSON from {file_path}: {e}")
        return default


def verify_file_write(file_path: str, min_size: int = 0) -> bool:
    """
    Verify that a file was written successfully.
    
    Args:
        file_path: File path to verify
        min_size: Minimum expected file size in bytes
    
    Returns:
        bool: True if file exists and meets size requirement
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return False
        
        if file_path.stat().st_size < min_size:
            return False
        
        return True
        
    except Exception as e:
        print(f"Error verifying file {file_path}: {e}")
        return False


def safe_image_write(image_path: str, image_data, cv2_module) -> bool:
    """
    Safely write image with OpenCV with verification.
    
    Args:
        image_path: Target image file path
        image_data: Image numpy array
        cv2_module: OpenCV module (cv2)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        image_path = Path(image_path)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write image
        success = cv2_module.imwrite(str(image_path), image_data)
        
        if not success:
            print(f"cv2.imwrite failed for {image_path}")
            return False
        
        # Verify file was written
        if not verify_file_write(str(image_path), min_size=100):
            print(f"Image verification failed for {image_path}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error in safe_image_write({image_path}): {e}")
        return False


@contextmanager
def safe_video_writer(output_path: str, fourcc, fps: float, 
                      frame_size: tuple, cv2_module):
    """
    Context manager for safe VideoWriter with guaranteed cleanup.
    
    Args:
        output_path: Output video file path
        fourcc: Video codec fourcc code
        fps: Frames per second
        frame_size: Frame size as (width, height)
        cv2_module: OpenCV module (cv2)
    
    Yields:
        VideoWriter object
    
    Example:
        with safe_video_writer('output.mp4', fourcc, 20.0, (640, 480), cv2) as writer:
            for frame in frames:
                writer.write(frame)
    """
    writer = None
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create VideoWriter
        writer = cv2_module.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            frame_size
        )
        
        if not writer.isOpened():
            raise IOError(f"Could not open VideoWriter for {output_path}")
        
        yield writer
        
    finally:
        # Ensure VideoWriter is always released
        if writer is not None:
            try:
                writer.release()
            except Exception as e:
                print(f"Error releasing VideoWriter: {e}")


def ensure_directory(dir_path: str) -> bool:
    """
    Safely ensure directory exists with error handling.
    
    Args:
        dir_path: Directory path to create
    
    Returns:
        bool: True if directory exists or was created successfully
    """
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {dir_path}: {e}")
        return False
