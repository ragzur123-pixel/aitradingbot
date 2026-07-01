import time
import logging
import functools
import json
import google.api_core.exceptions
from logging.handlers import RotatingFileHandler

class JsonFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format."""
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "thread": record.threadName,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging(name, json_format=True):
    """Setup standard logging configuration with rotating file handler."""
    log_file = f"{name}.log" if name != "root" else "trading_system.log"
    max_bytes = 5 * 1024 * 1024  # 5MB
    backup_count = 3
    
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s'
        )
    
    # Create handler
    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    handler.setFormatter(formatter)
    
    # Stream handler for console (keep plain text for readability)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S'
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    
    # Get logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger

def retry_with_backoff(max_retries=5, initial_delay=2, backoff_factor=2):
    """Decorator for retrying API calls with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (google.api_core.exceptions.ResourceExhausted, 
                        google.api_core.exceptions.ServiceUnavailable,
                        google.api_core.exceptions.InternalServerError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logging.error(f"Max retries reached for {func.__name__}. Error: {e}")
                        raise e
                    logging.warning(f"API Error ({e}). Retrying in {delay}s (Attempt {retries}/{max_retries})...")
                    time.sleep(delay)
                    delay *= backoff_factor
                except Exception as e:
                    logging.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise e
            return None
        return wrapper
    return decorator
