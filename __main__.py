import json
import os
import random
import sys
import time
import urllib.parse
from datetime import datetime

import feedparser
import schedule
import trafilatura
import ollama
from googlenewsdecoder import gnewsdecoder
from loguru import logger

# Configuration
TICKERS = ["AAPL", "MSFT", "TSLA"]
OLLAMA_MODEL = "gemma4:e4b"
BLACKLIST_FILE = "domain_blacklist.json"

# Configure Loguru
logger.remove()
logger.add(
    sys.stderr, 
    level="DEBUG", 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
)

def load_blacklist():
    """Loads the blacklisted domains from a local file."""
    if os.path.exists(BLACKLIST_FILE):
        try:
            with open(BLACKLIST_FILE, "r") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()

def save_blacklist(blacklist_set):
    """Saves the blacklisted domains to a local file."""
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(list(blacklist_set), f)

# Initialize global blacklist
BLACKLIST = load_blacklist()

def analyze_for_stocks(text):
    """Passes extracted text to local Ollama instance to hunt for stock tickers."""
    prompt = f"""You are a financial analyst. Read the following news article and identify any publicly traded companies mentioned. 

Return a list in the following format:
- TICKER: [1-sentence reason why it is mentioned and potential impact]

If no publicly traded companies are mentioned in the text, respond strictly with 'NO TICKERS FOUND'.

Article text:
{text}"""
    
    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
        return response.get("response", "No analysis generated.").strip()
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}")
        return "ERROR"

def process_article(article):
    """Decodes, extracts, and analyzes a single news article for stock ideas."""
    decoded = gnewsdecoder(article.link)
    real_link = decoded.get("decoded_url") if decoded.get("status") else article.link

    # Validate URL
    if not real_link or not (real_link.startswith("http://") or real_link.startswith("https://")):
        logger.debug("Skipped: No valid URL available.")
        return False

    domain = urllib.parse.urlparse(real_link).netloc

    # Check Blacklist
    if domain in BLACKLIST:
        logger.debug(f"Skipped: Domain '{domain}' is blacklisted.")
        return False

    logger.debug(f"Processing Article: {article.title}")
    logger.debug(f"Source: {article.source.title} | Link: {real_link}")

    logger.debug("Extracting content with Trafilatura...")
    downloaded_html = trafilatura.fetch_url(real_link)

    if not downloaded_html:
        logger.warning(f"Failed to download the page. Adding '{domain}' to blacklist.")
        BLACKLIST.add(domain)
        save_blacklist(BLACKLIST)
        return False

    extracted_text = trafilatura.extract(downloaded_html)
    
    if not extracted_text:
        logger.debug("Skipped: Could not extract text content.")
        return False

    logger.debug(f"Scanning for potential investments with {OLLAMA_MODEL}...")
    analysis = analyze_for_stocks(extracted_text)
    
    if analysis == "ERROR":
        return False

    # Filter out empty results to the DEBUG level, elevate discoveries to INFO
    if "NO TICKERS FOUND" in analysis.upper():
        logger.debug("AI Analysis: No actionable stocks found in this article.")
    else:
        logger.info(f"AI Stock Discovery [{article.source.title}]:\n{analysis}\n")

    return True

def fetch_news_for_query(query, header_message, target_articles=2, max_attempts=15):
    """Fetches Google News RSS for a query and processes until target is met or max is reached."""
    logger.debug(header_message)
    
    encoded_topic = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)

    successful_articles = 0
    total_attempts = 0

    for article in feed.entries:
        if successful_articles >= target_articles:
            logger.debug(f"Reached target of {target_articles} successful articles for query.")
            break
        
        if total_attempts >= max_attempts:
            logger.warning(f"Reached hard limit of {max_attempts} total attempts for query. Stopping.")
            break

        total_attempts += 1
        success = process_article(article)

        if success:
            successful_articles += 1
            time.sleep(random.uniform(1.5, 3.5))

def fetch_discovery_news(target_articles=3):
    """Fetches broad business and tech news to find new stocks."""
    topics = ["emerging technology breakthrough", "business acquisition rumors", "supply chain disruption"]
    
    for topic in topics:
        fetch_news_for_query(topic, f"Hunting for stocks in topic: {topic}", target_articles)

def fetch_stock_news(target_articles=2):
    """Fetches top financial news for predefined tickers using Google News RSS."""
    logger.debug("Fetching News for Portfolio Tickers")
    
    for ticker in TICKERS:
        query = f"{ticker} stock market"
        fetch_news_for_query(query, f"Latest News for {ticker}:", target_articles)

def scheduled_job():
    """Wrapper function to run all news gathering tasks."""
    logger.debug(f"--- RUNNING SCHEDULED FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    # 1. Look for new stock ideas in general tech/business news
    fetch_discovery_news(target_articles=2)
    
    # 2. Check up on the existing portfolio
    fetch_stock_news(target_articles=1)

if __name__ == "__main__":
    scheduled_job()
    schedule.every(60).minutes.do(scheduled_job)
    
    logger.debug("Stock Discovery Scheduler active. Waiting for next job...")
    while True:
        schedule.run_pending()
        time.sleep(1)
