import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_str: Optional[str] = None,
    log_file: Optional[str] = None,  # Ignorado - apenas para compatibilidade
) -> logging.Logger:
    """
    Set up and configure a logger com output apenas para console (CloudWatch).

    Args:
        name: The name of the logger
        level: The logging level (default: INFO)
        format_str: Optional custom format string
        log_file: Ignorado (mantido para compatibilidade)

    Returns:
        A configured logger instance
    """
    if format_str is None:
        format_str = "%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers if they already exist
    if not logger.handlers:
        # Console handler apenas (CloudWatch)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(format_str))
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger


# Create a default app_logger instance that can be imported by other modules
app_logger = setup_logger("app") 