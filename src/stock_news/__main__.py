from datetime import datetime
from loguru import logger

from stock_news.config import setup_logging
from stock_news.news import fetch_discovery_news
from stock_news.utils import init_db

def main():
    """Entry point for command line execution."""
    setup_logging()
    init_db()
    logger.debug(
        f"--- RUNNING FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
    )
    fetch_discovery_news()

if __name__ == "__main__":
    main()
