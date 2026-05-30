import feedparser
from googlenewsdecoder import gnewsdecoder
import time
import random

url = "https://news.google.com/rss/search?q=AI+Automation&hl=en-US&gl=US&ceid=US:en"
feed = feedparser.parse(url)

for article in feed.entries[:3]:
    # The decoder handles the API endpoints, rate limiting, and proxies under the hood
    decoded = gnewsdecoder(article.link)
    
    real_link = decoded.get("decoded_url") if decoded.get("status") else article.link

    print(f"Title: {article.title}")
    print(f"Source: {article.source.title}")
    print(f"Real Link: {real_link}\n")
    print("-" * 40)
    
    delay = random.uniform(1.5, 3.5)
    time.sleep(delay)
