import random
import time
import urllib.parse
from datetime import datetime

import feedparser
import schedule
import trafilatura
import ollama
from googlenewsdecoder import gnewsdecoder

# Configuration
TICKERS = ["AAPL", "MSFT", "TSLA"]
OLLAMA_MODEL = "gemma4:e4b"

def analyze_for_stocks(text):
    """Passes extracted text to local Ollama instance to hunt for stock tickers."""
    prompt = f"""You are a financial analyst. Read the following news article and identify any publicly traded companies mentioned. 

Return a list in the following format:
- TICKER: [1-sentence reason why it is mentioned and potential impact]

If no publicly traded companies are mentioned in the text, respond strictly with 'NO TICKERS FOUND'.

Article text:
{text}"""
    
    try:
        # Calls your local Ollama server API running on localhost:11434
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
        return response.get("response", "No analysis generated.").strip()
    except Exception as e:
        return f"[Ollama Error: Make sure your local server is running. Details: {e}]"

def process_article(article):
    """Decodes, extracts, and analyzes a single news article for stock ideas."""
    decoded = gnewsdecoder(article.link)
    real_link = decoded.get("decoded_url") if decoded.get("status") else article.link

    print(f"Title: {article.title}")
    print(f"Source: {article.source.title}")
    print(f"Link: {real_link}")

    # Validate URL
    if not real_link or not (real_link.startswith("http://") or real_link.startswith("https://")):
        print("Article Preview: Skipped (No valid URL available).\n")
        return

    print("Extracting content with Trafilatura...")
    downloaded_html = trafilatura.fetch_url(real_link)

    if not downloaded_html:
        print("Article Preview: Failed to download the page.\n")
        return

    extracted_text = trafilatura.extract(downloaded_html)
    
    if not extracted_text:
        print("Article Preview: Could not extract text content.\n")
        return

    print(f"Scanning for potential investments with {OLLAMA_MODEL}...")
    analysis = analyze_for_stocks(extracted_text)
    
    # Optional: Filter out empty results to keep the terminal clean
    if "NO TICKERS FOUND" in analysis.upper():
        print("--- AI Analysis ---\nNo actionable stocks found in this article.\n-------------------\n")
    else:
        print(f"\n--- AI Stock Discovery ---\n{analysis}\n--------------------------\n")

def fetch_news_for_query(query, header_message, max_articles=2):
    """Fetches Google News RSS for a query and processes the top articles."""
    print(f"{header_message}\n" + "=" * 40)
    
    encoded_topic = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)

    for article in feed.entries[:max_articles]:
        process_article(article)
        print("*" * 40)
        time.sleep(random.uniform(1.5, 3.5))

def fetch_discovery_news(max_articles=3):
    """Fetches broad business and tech news to find new stocks."""
    # Using broader topics increases the chance of discovering lesser-known companies
    topics = ["emerging technology breakthrough", "business acquisition rumors", "supply chain disruption"]
    
    for topic in topics:
        fetch_news_for_query(topic, f"Hunting for stocks in topic: {topic}", max_articles)

def fetch_stock_news(max_articles=2):
    """Fetches top financial news for predefined tickers using Google News RSS."""
    print(f"Fetching News for Portfolio Tickers\n" + "=" * 40)
    
    for ticker in TICKERS:
        query = f"{ticker} stock market"
        fetch_news_for_query(query, f"\nLatest News for {ticker}:", max_articles)

def scheduled_job():
    """Wrapper function to run all news gathering tasks."""
    print(f"\n{'#'*60}")
    print(f"RUNNING SCHEDULED FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*60}\n")
    
    # 1. Look for new stock ideas in general tech/business news
    fetch_discovery_news(max_articles=2)
    print("\n")
    
    # 2. Check up on the existing portfolio
    fetch_stock_news(max_articles=1)

if __name__ == "__main__":
    scheduled_job()
    schedule.every(60).minutes.do(scheduled_job)
    
    print("\nStock Discovery Scheduler active. Keep this script running...")
    while True:
        schedule.run_pending()
        time.sleep(1)
