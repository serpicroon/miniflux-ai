import threading
from pathlib import Path

from .config import config
from .logger import logger


# File paths
SUMMARY_FILE = Path('data/summary.dat')
DIGEST_FILE = Path('data/digest.dat')

# Shared file lock to prevent concurrent read/write issues
SUMMARY_FILE_LOCK = threading.Lock()
DIGEST_FILE_LOCK = threading.Lock()

# Global shutdown event to signal all threads/processes to stop
shutdown_event = threading.Event()
