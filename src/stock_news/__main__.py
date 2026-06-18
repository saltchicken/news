from datetime import datetime
from loguru import logger

from stock_news.config import setup_logging
from stock_news.news import fetch_discovery_news

def main():
    """Entry point for command line execution."""
    setup_logging()
    logger.debug(
        f"--- RUNNING FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
    )
    fetch_discovery_news()

if __name__ == "__main__":
    main()
