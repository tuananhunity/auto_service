import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(log_dir="logs", level=logging.INFO):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, 'bot_execution.log')
    logger = logging.getLogger('FacebookAICommentBot')
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        # File Handler with rotation (10 MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Standard Output (Console) Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger

# Global instance for shared usage
GLOBAL_LOGGER = setup_logger()
