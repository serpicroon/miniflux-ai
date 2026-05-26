import threading
from pathlib import Path

from .config import config
from .exceptions import LLMResponseError
from .logger import get_logger

__all__ = [
    "config",
    "LLMResponseError",
    "get_logger",
    "SUMMARY_FILE",
    "DIGEST_FILE",
    "SUMMARY_FILE_LOCK",
    "DIGEST_FILE_LOCK",
    "shutdown_event",
]

# File paths
SUMMARY_FILE = Path("data/summary.dat")
DIGEST_FILE = Path("data/digest.dat")

# Shared file lock to prevent concurrent read/write issues
SUMMARY_FILE_LOCK = threading.Lock()
DIGEST_FILE_LOCK = threading.Lock()

# Global shutdown event to signal all threads/processes to stop
shutdown_event = threading.Event()
