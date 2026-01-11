import logging
import sys

def setup_logger():
    """Sets up a simple logger that outputs to console."""
    logger = logging.getLogger("StreamDownloader")
    logger.setLevel(logging.DEBUG)
    
    # Avoid adding multiple handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        # Format: [TIME] [LEVEL] Message
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

log = setup_logger()
