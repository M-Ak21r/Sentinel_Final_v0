# File Utilities - Quick Reference Guide

## Import Statement
```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'Shared'))
from libs.file_utils import (
    FileLock, 
    atomic_write_json, 
    atomic_append_csv, 
    safe_read_json,
    safe_image_write, 
    safe_video_writer, 
    ensure_directory
)
```

## Common Use Cases

### 1. Writing JSON Files (Thread-Safe & Atomic)
```python
# OLD - UNSAFE
with open('events.json', 'w') as f:
    json.dump(data, f)

# NEW - SAFE
atomic_write_json('events.json', data, indent=2)
```

### 2. Reading JSON Files (With File Locking)
```python
# OLD - UNSAFE
with open('events.json', 'r') as f:
    data = json.load(f)

# NEW - SAFE
data = safe_read_json('events.json', default=[])
```

### 3. Appending to CSV Files (Thread-Safe)
```python
# OLD - UNSAFE
with open('alerts.csv', 'a', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([timestamp, alert_type, severity])

# NEW - SAFE
atomic_append_csv(
    'alerts.csv',
    [timestamp, alert_type, severity],
    header=['Timestamp', 'Alert Type', 'Severity']  # Only for new files
)
```

### 4. Saving Images (With Verification)
```python
# OLD - UNSAFE
cv2.imwrite('evidence.jpg', frame)

# NEW - SAFE
if not safe_image_write('evidence.jpg', frame, cv2):
    logger.error("Failed to save image")
```

### 5. Recording Videos (With Automatic Cleanup)
```python
# OLD - UNSAFE (VideoWriter leak!)
writer = cv2.VideoWriter('video.mp4', fourcc, fps, (w, h))
for frame in frames:
    writer.write(frame)
writer.release()  # May not execute if exception occurs!

# NEW - SAFE (Context manager ensures cleanup)
with safe_video_writer('video.mp4', fourcc, fps, (w, h), cv2) as writer:
    for frame in frames:
        writer.write(frame)
# Automatic release even on exceptions
```

### 6. Creating Directories Safely
```python
# OLD - UNSAFE
os.makedirs(directory, exist_ok=True)

# NEW - SAFE (with error handling)
if not ensure_directory(directory):
    logger.error(f"Failed to create directory: {directory}")
```

### 7. Manual File Locking
```python
# For complex operations requiring explicit lock control
with FileLock('/path/to/file.lock', timeout=10.0):
    # Critical section - only one process/thread at a time
    with open('shared_file.txt', 'r+') as f:
        data = f.read()
        f.seek(0)
        f.write(modified_data)
        f.truncate()
```

## Migration Checklist

When updating existing code:

- [ ] Replace `json.dump()` with `atomic_write_json()`
- [ ] Replace `json.load()` with `safe_read_json()`
- [ ] Replace CSV writes with `atomic_append_csv()`
- [ ] Replace `cv2.imwrite()` with `safe_image_write()`
- [ ] Replace VideoWriter with `safe_video_writer()` context manager
- [ ] Replace `os.makedirs()` with `ensure_directory()`
- [ ] Add `sys.path.insert()` to import file_utils

## Common Pitfalls to Avoid

### ❌ DON'T: Pass VideoWriter objects between threads
```python
# BAD - Race condition!
queue.put(('video', video_writer, frame))
```

### ✅ DO: Write frames synchronously with lock protection
```python
# GOOD
with self.video_writer_lock:
    if self.video_writer:
        self.video_writer.write(frame)
```

### ❌ DON'T: Forget to check return values
```python
# BAD
safe_image_write('evidence.jpg', frame, cv2)
```

### ✅ DO: Always check success
```python
# GOOD
if not safe_image_write('evidence.jpg', frame, cv2):
    logger.error("Image write failed")
    return None
```

### ❌ DON'T: Use unbounded queues for file operations
```python
# BAD - Memory exhaustion risk
self.queue = queue.Queue()
```

### ✅ DO: Use bounded queues with overflow handling
```python
# GOOD
self.queue = queue.Queue(maxsize=100)

def queue_task(self, task):
    try:
        self.queue.put(task, block=False)
    except queue.Full:
        logger.warning("Queue full, dropping task")
```

## Performance Tips

1. **Batch Operations**: Group multiple small writes into one large write
2. **Cache Reads**: Read once, use many times instead of repeated file access
3. **Async Images**: Use bounded queue for image writes (non-critical)
4. **Sync Videos**: Always write video frames synchronously (critical for integrity)

## Troubleshooting

### Lock Timeout Errors
```
TimeoutError: Could not acquire lock on file.lock within 10 seconds
```
**Solution**: Increase timeout or check for deadlocks

### Queue Full Warnings
```
WARNING: Evidence writer queue full, dropping task
```
**Solution**: Normal under high load - evidence is being generated faster than disk can write

### Failed Image Writes
```
ERROR: Failed to save evidence image: /path/to/image.jpg
```
**Solution**: Check disk space and file permissions

## Testing Your Implementation

```python
import pytest
from libs.file_utils import atomic_write_json, safe_read_json

def test_atomic_write_survives_crash():
    """Test that atomic writes don't corrupt files on crash."""
    # Write initial data
    atomic_write_json('test.json', {'count': 0})
    
    # Simulate crash during write (in separate process)
    # Original file should remain intact
    data = safe_read_json('test.json', default={})
    assert data == {'count': 0}

def test_concurrent_writes():
    """Test that concurrent writes don't corrupt files."""
    import threading
    
    def writer(i):
        for j in range(100):
            atomic_write_json(f'test_{i}.json', {'thread': i, 'iteration': j})
    
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # All files should be valid JSON
    for i in range(10):
        data = safe_read_json(f'test_{i}.json')
        assert data is not None
```

---

**Remember**: File corruption bugs are hard to reproduce and debug. Always use these utilities for any file operations in the Sentinel system.
