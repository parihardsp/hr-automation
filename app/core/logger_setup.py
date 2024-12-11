import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

# Create a single logger instance
logger = None


def setup_logger(name="hr_automation", log_folder="logs", backup_count=7):
    global logger
    if logger is not None:
        return logger

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    logger.handlers.clear()

    # Prevent propagation
    logger.propagate = False

    # Create log directory in project root
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(root_dir, log_folder)
    os.makedirs(log_dir, exist_ok=True)

    # Set up file handler
    current_date = datetime.now().strftime('%Y_%m_%d')
    log_file_path = os.path.join(log_dir, f"app_{current_date}.log")

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",
        interval=1,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Initialize the logger
logger = setup_logger()

# Export the logger instance
__all__ = ['logger']

