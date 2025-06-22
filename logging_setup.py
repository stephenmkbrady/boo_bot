import logging
import sys
from pathlib import Path

def setup_logging(level: str = "INFO", log_file: str = "bot.log"):
    """Set up structured logging"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(f"logs/{log_file}"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set up logger for matrix-nio
    logging.getLogger("nio").setLevel(logging.WARNING)
    
    # Set up logger for urllib3 (used by aiohttp)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Set up logger for aiohttp
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    return logging.getLogger("bot")