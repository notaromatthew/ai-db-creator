import os
import sys

from loguru import logger


def setup_logger(level: str | None = None):
    """Log su stdout/stderr (raccolti da Coolify). In produzione JSON, senza file locali.

    Il file di log giornaliero resta solo in sviluppo (LOG_TO_FILE=1).
    """
    level = level or os.getenv("LOG_LEVEL", "DEBUG")
    logger.remove()
    if os.getenv("LOG_FORMAT", "").lower() == "json":
        logger.add(sys.stderr, level=level, serialize=True)
    else:
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )
    if os.getenv("LOG_TO_FILE", "0") == "1":
        logger.add("logs/app_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days", level=level)
    return logger


log = setup_logger()
