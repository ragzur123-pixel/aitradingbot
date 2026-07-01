import os
import time
import logging

class FileLock:
    """Simple cross-platform file locking mechanism."""
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.handle = None

    def acquire(self, timeout=10):
        """Wait for the lock file to be released."""
        start_time = time.time()
        while os.path.exists(self.lock_file):
            if time.time() - start_time > timeout:
                logging.warning(f"Lock timeout for {self.lock_file}. Proceeding with caution.")
                break
            time.sleep(0.1)
        
        try:
            with open(self.lock_file, "w") as f:
                f.write(str(os.getpid()))
        except: pass

    def release(self):
        """Delete the lock file."""
        if os.path.exists(self.lock_file):
            try:
                os.remove(self.lock_file)
            except: pass

def atomic_write_json(file_path, data):
    """Safely write JSON to a file using a temporary file and locking."""
    import json
    lock = FileLock(file_path + ".lock")
    lock.acquire()
    try:
        temp_path = file_path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, file_path)
    finally:
        lock.release()

def atomic_read_json(file_path, default=None):
    """Safely read JSON from a file with locking."""
    import json
    if not os.path.exists(file_path):
        return default
    
    lock = FileLock(file_path + ".lock")
    lock.acquire()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default
    finally:
        lock.release()
