import logging
import os
from pathlib import Path
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger for the API Automation Framework.
    
    Creates a rotating log file inside the 'logs/' directory and also
    outputs log messages to the console.

    Args:
        name (str): The name of the logger (usually __name__).

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    is_trial = os.environ.get("TRIAL_RUN") == "true"
    prefix = "trial_" if is_trial else ""
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    current_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    log_file = log_dir / f"{prefix}execution_{current_date}.log"

    # Cleanup old logs (keep only the latest one)
    try:
        log_files = sorted(log_dir.glob(f"{prefix}execution_*.log"))
        for old_log in log_files:
            try:
                os.remove(old_log)
            except OSError:
                pass
    except Exception:
        pass

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # File Handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
