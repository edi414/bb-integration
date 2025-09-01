import logging
import os
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_str: Optional[str] = None,
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Set up and configure a logger with consistent formatting.

    Args:
        name: The name of the logger
        level: The logging level (default: INFO)
        format_str: Optional custom format string
        log_file: Optional path to log file for file-based logging
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)

    Returns:
        A configured logger instance
    """
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(console_handler)

        # File handler if specified
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setFormatter(logging.Formatter(format_str))
            logger.addHandler(file_handler)

    logger.propagate = False
    return logger


# Create a default app_logger instance that can be imported by other modules
app_logger = setup_logger(
    "app",
    log_file=os.path.join("logs", "app.log")
) 