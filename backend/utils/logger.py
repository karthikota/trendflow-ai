import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict
from backend.config import settings

class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter that outputs structured logs in JSON format.
    Perfect for programmatic ingestion, log monitoring tools, or n8n notifications.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Construct standard fields
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Include traceback details if an exception was raised
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include custom fields passed through the `extra` argument in logging calls
        # (Filter out system-defined attributes from log record)
        system_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName", "processName",
            "process"
        }
        extra_data = {k: v for k, v in record.__dict__.items() if k not in system_attrs}
        if extra_data:
            log_data["extra"] = extra_data

        return json.dumps(log_data)

def setup_logger(name: str = "trendflow") -> logging.Logger:
    """
    Initializes a dual-stream logger:
    1. Human-readable standard console handler (stdout)
    2. Machine-readable structured JSON handler (logs/trendflow.json)
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding duplicate handlers if logger is already configured
    if logger.handlers:
        return logger

    # Ensure directories exist before configuring logging
    settings.ensure_directories()
    
    # 1. Console Handler - Readable and concise
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-7s - %(name)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (JSON) - Detailed and structured
    log_file_path = os.path.join(settings.LOGS_DIR, "trendflow.json")
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)

    return logger

# Create a shared default logger instance
logger = setup_logger("trendflow")
