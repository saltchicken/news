import random
import time
import urllib.parse

import feedparser
from loguru import logger

from stock_news.fetcher import process_article


def fetch_news_for_query(query, header_message, timeframe="1h"):
    """Fetches Google News RSS for a query and processes all articles found within the timeframe."""
    logger.debug(header_message)
    recent_query = f"{query} when:{timeframe}"
    encoded_topic = urllib.parse.quote_plus(recent_query)

    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)

    for article in feed.entries:
        success = process_article(article, query)
        if success:
            time.sleep(random.uniform(1.5, 3.5))


def fetch_discovery_news():
    """Fetches broad business and tech news to find new stocks."""
    topics = [
        # Original topics
        "emerging technology breakthrough",
        "business acquisition rumors",
        "supply chain disruption",

        # New Earnings-specific topics
        "earnings beat expectations revenue",
        "slashes revenue forecast outlook",
        "raises full year guidance",
        "operating loss widens"
    ]

    for topic in topics:
        fetch_news_for_query(
            query=topic, header_message=f"Hunting for stocks in topic: {topic}")
