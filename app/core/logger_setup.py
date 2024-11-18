import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

def setup_logger(log_folder="logs", backup_count=7):
    os.makedirs(log_folder, exist_ok=True)

    logger = logging.getLogger("hr_automation")
    logger.setLevel(logging.DEBUG)

    # Create a log file path with the current date
    current_date = datetime.now().strftime('%Y_%m_%d')
    log_file_path = os.path.join(log_folder, f"app_{current_date}.log")  # Directly using the formatted log file name

    # Create a handler that rotates logs every midnight
    file_handler = TimedRotatingFileHandler(
        log_file_path,
        when="midnight",
        interval=1,
        backupCount=backup_count,
    )
    # Create a custom formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger

# Example usage
if __name__ == "__main__":
    logger = setup_logger()
    logger.info("Logger is set up successfully.")
