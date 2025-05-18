#backend/utils/logger.py
import logging
import sys
from datetime import datetime

#basic logger setup, can be expanded with file logging, structured logging, etc.

def setup_logger(name="app_logger", level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.hasHandlers(): #ensure handlers are not added multiple times
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

#example usage:
#app_logger = setup_logger()
#app_logger.info("This is an info message.")

#for game event logging, the Grimoire.log_event is primary.
#this logger can be for system/application level logging.

#function to generate a structured log entry for game events (alternative to Grimoire method if needed elsewhere)
def create_game_log_entry(event_type: str, data: dict, timestamp_override: datetime = None) -> dict:
    return {
        "timestamp": timestamp_override or datetime.utcnow().isoformat(),
        "event_type": event_type,
        "data": data
    } 