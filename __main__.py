import random
import time
import urllib.parse

import feedparser
from googlenewsdecoder import gnewsdecoder


def fetch_google_news(topic, max_articles=3):
    """Fetches and decodes recent Google News articles for a specific topic."""

    # Safely encode the topic to handle spaces and special characters
    encoded_topic = urllib.parse.quote_plus(topic)

    # Inject the encoded topic into the URL
    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    print(f"Fetching news for: {topic}\n" + "=" * 40)

    for article in feed.entries[:max_articles]:
        # The decoder handles the API endpoints, rate limiting, and proxies under the hood
        decoded = gnewsdecoder(article.link)

        real_link = decoded.get("decoded_url") if decoded.get(
            "status") else article.link

        print(f"Title: {article.title}")
        print(f"Source: {article.source.title}")
        print(f"Published: {article.published}")  # <-- Added publication date
        print(f"Real Link: {real_link}\n")
        print("-" * 40)

        delay = random.uniform(1.5, 3.5)
        time.sleep(delay)


if __name__ == "__main__":
    fetch_google_news("San Jose")
