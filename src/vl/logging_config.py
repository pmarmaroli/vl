"""
VL Logging Configuration
Centralized logging setup for the VL compiler/interpreter

Usage:
    from vl_logging import get_logger
    
    logger = get_logger(__name__)
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
"""

import logging
import sys
from typing import Optional


# Global log level (can be set programmatically)
_log_level = logging.INFO


class InfoFilter(logging.Filter):
    """Filter to send INFO and DEBUG to stdout, WARNING+ to stderr"""
    def filter(self, record):
        return record.levelno <= logging.INFO


def setup_logging(level: Optional[int] = None, debug: bool = False):
    """
    Setup logging configuration for VL
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        debug: If True, sets level to DEBUG
    """
    global _log_level
    
    if debug:
        _log_level = logging.DEBUG
    elif level is not None:
        _log_level = level
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Handler for INFO and DEBUG -> stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(InfoFilter())
    stdout_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                         datefmt='%H:%M:%S')
    )
    
    # Handler for WARNING and above -> stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                         datefmt='%H:%M:%S')
    )
    
    # Configure root logger
    root_logger.setLevel(_log_level)
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(stderr_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(_log_level)
    return logger


def set_log_level(level: int):
    """
    Set global log level
    
    Args:
        level: Logging level constant from logging module
    """
    global _log_level
    _log_level = level
    logging.getLogger().setLevel(level)


# Convenience functions
def enable_debug():
    """Enable debug logging"""
    set_log_level(logging.DEBUG)


def disable_debug():
    """Disable debug logging (set to INFO)"""
    set_log_level(logging.INFO)


def quiet_mode():
    """Set logging to WARNING only"""
    set_log_level(logging.WARNING)


# Initialize default logging
setup_logging()
