import time
from datetime import datetime
from loguru import logger
import schedule

from stock_news.config import setup_logging
from stock_news.news import fetch_discovery_news

def scheduled_job():
    """Wrapper function to run all news gathering tasks."""
    logger.debug(
        f"--- RUNNING SCHEDULED FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
    )
    fetch_discovery_news()

def main():
    """Entry point for command line execution."""
    setup_logging()
    scheduled_job()
    schedule.every(60).minutes.do(scheduled_job)

    logger.debug("Stock Discovery Scheduler active. Waiting for next job...")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
