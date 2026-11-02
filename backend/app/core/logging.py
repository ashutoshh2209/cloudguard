import logging
import sys
from .config import settings

def setup_logging():
    """
    Configure application logging.
    In development, uses readable text formats.
    In production, this would typically use JSON formatted logs.
    """
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    
    # Basic configuration
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Configure specific loggers
    # Silence chatty third-party loggers and prevent botocore from logging raw AWS STS headers/tokens
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logger = logging.getLogger(settings.APP_NAME)
    logger.info(f"Logging configured for {settings.ENVIRONMENT} environment")
    
    return logger

logger = setup_logging()
