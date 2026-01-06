import logging
from functools import cache
from typing import Dict, Any, Optional

from .config import config


class _Logger:
    """
    Custom logger wrapper with entry-specific logging methods.
    
    Usage:
        from common.logger import get_logger
        
        logger = get_logger(__name__)
        
        # Standard logging
        logger.info("Processing started")
        logger.debug("Debug message")
        
        # Entry-specific logging
        logger.info_entry(entry, message="Complete", agent_name="Summarizer")
        logger.debug_entry(entry, include_content=True)
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize logger with given name.
        
        Args:
            name: Logger name, typically __name__ of the calling module.
        """
        if name is None:
            name = "miniflux-ai"
        
        log = logging.getLogger(name)
        log.setLevel(config.log_level)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        log.addHandler(console)
        log.propagate = False
        
        self._logger = log
    
    # Standard logging methods (proxy to underlying logger)
    def debug(self, msg: str, *args, **kwargs) -> None:
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        self._logger.error(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        self._logger.exception(msg, *args, **kwargs)
    
    # Entry-specific logging methods
    def debug_entry(
        self,
        entry: Optional[Dict[str, Any]],
        agent_name: Optional[str] = None,
        message: str = "",
        include_title: bool = False,
        include_content: bool = False,
    ) -> None:
        """Log entry at DEBUG level. include_content only works at this level."""
        self._log_entry(
            entry,
            level=logging.DEBUG,
            agent_name=agent_name,
            message=message,
            include_title=include_title,
            include_content=include_content,
        )
    
    def info_entry(
        self,
        entry: Optional[Dict[str, Any]],
        agent_name: Optional[str] = None,
        message: str = "",
        include_title: bool = False,
    ) -> None:
        """Log entry at INFO level."""
        self._log_entry(
            entry,
            level=logging.INFO,
            agent_name=agent_name,
            message=message,
            include_title=include_title,
        )
    
    def warning_entry(
        self,
        entry: Optional[Dict[str, Any]],
        agent_name: Optional[str] = None,
        message: str = "",
        include_title: bool = False,
    ) -> None:
        """Log entry at WARNING level."""
        self._log_entry(
            entry,
            level=logging.WARNING,
            agent_name=agent_name,
            message=message,
            include_title=include_title,
        )
    
    def error_entry(
        self,
        entry: Optional[Dict[str, Any]],
        agent_name: Optional[str] = None,
        message: str = "",
        include_title: bool = False,
    ) -> None:
        """Log entry at ERROR level."""
        self._log_entry(
            entry,
            level=logging.ERROR,
            agent_name=agent_name,
            message=message,
            include_title=include_title,
        )
    
    def _log_entry(
        self,
        entry: Optional[Dict[str, Any]],
        level: int = logging.INFO,
        agent_name: Optional[str] = None,
        message: str = "",
        include_title: bool = False,
        include_content: bool = False,
    ) -> None:
        """
        Unified logging method for entry processing with standardized format.
        
        Log output order: entry_id, agent_name, title, message, content
        
        Args:
            entry: Entry dictionary, can be None
            level: Log level (logging.DEBUG, logging.INFO, etc.)
            agent_name: Agent name (optional)
            message: Log message
            include_title: Whether to include entry title
            include_content: Whether to include entry content (only effective at DEBUG level)
        """
        entry = entry or {}
        entry_id = entry.get('id', 'unknown')
        
        parts = [f"Entry {entry_id}"]
        
        if agent_name:
            parts.append(f"Agent {agent_name}")

        if include_title and entry.get('title'):
            entry_title = entry['title']
            if len(entry_title) > 100:
                entry_title = entry_title[:100] + "..."
            parts.append(f"Title: {entry_title}")
        
        if message:
            message_preview = message.replace("\n", "\\n")
            if len(message_preview) > 1000:
                message_preview = message_preview[:1000] + "..."
            parts.append(message_preview)
        
        # Content only logged at DEBUG level to avoid verbose logs
        if include_content and level == logging.DEBUG and entry.get('content'):
            content = entry['content']
            content_preview = content.replace("\n", "\\n")
            if len(content_preview) > 1000:
                content_preview = content_preview[:1000] + "..."
            parts.append(f"Content: {content_preview}")
        
        log_message = " - ".join(parts)
        self._logger.log(level, log_message)


@cache
def get_logger(name: Optional[str] = None) -> _Logger:
    """
    Get a Logger instance. Cached to ensure same name returns same instance.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
    
    Returns:
        Logger instance
    
    Usage:
        from common.logger import get_logger
        
        logger = get_logger(__name__)
        
        # Standard logging
        logger.info("Processing started")
        
        # Entry-specific logging
        logger.info_entry(entry, message="Complete")
    """
    return _Logger(name)
