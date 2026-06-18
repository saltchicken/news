import sys

from loguru import logger

OLLAMA_MODEL = "gemma4:e4b"
DB_FILE = "stock_news.db"


def setup_logging():
    """Configures the central Loguru logger."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG",
        format=
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
    )
