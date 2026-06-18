import argparse
from datetime import datetime

from loguru import logger

from stock_news.config import setup_logging
from stock_news.news import fetch_discovery_news
from stock_news.utils import init_db
from stock_news.utils import print_recent_findings


def main():
    """Entry point for command line execution."""
    parser = argparse.ArgumentParser(description="Stock news scraper and analyzer")
    parser.add_argument("--fetch", action="store_true", help="Fetch news")
    parser.add_argument("--print", action="store_true", help="Print recent findings")
    parser.add_argument("--sentiment", type=str, choices=["Positive", "Negative", "Neutral", "positive", "negative", "neutral"], help="Filter findings by sentiment")
    parser.add_argument("--hours", type=int, default=24, help="Timeframe in hours for printing findings")
    parser.add_argument("--compact", action="store_true", help="Print only ticker and analysis")
    
    args = parser.parse_args()

    setup_logging()
    init_db()

    if args.fetch or not (args.fetch or args.print):
        logger.debug(
            f"--- RUNNING FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
        )
        fetch_discovery_news()

    if args.print:
        print_recent_findings(hours=args.hours, sentiment=args.sentiment, compact=args.compact)


if __name__ == "__main__":
    main()
