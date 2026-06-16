import json
import os
import random
import re
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
READ_ARTICLES_FILE = "read_articles.json"
DISCOVERIES_FILE = "stock_discoveries.json"
PORTFOLIO_NEWS_FILE = "portfolio_news.json"

# Configure Loguru
logger.remove()
logger.add(
    sys.stderr, 
    level="DEBUG", 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
)

def load_json_set(filepath):
    """Loads a JSON list as a set from a local file."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                return set(json.load(f))
        except json.JSONDecodeError:
            return set()
    return set()

def save_json_set(data_set, filepath):
    """Saves a set as a JSON list to a local file."""
    with open(filepath, "w") as f:
        json.dump(list(data_set), f)

def save_analysis(article_title, article_link, ticker_data, source, filepath):
    """Appends individual AI ticker analysis to the specified structured JSON file."""
    records = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                records = json.load(f)
        except json.JSONDecodeError:
            pass

    # Append a separate record for each ticker found in the article
    for item in ticker_data:
        records.append({
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "title": article_title,
            "link": article_link,
            "ticker": item.get("ticker", "UNKNOWN"),
            "analysis": item.get("reason", "No reason provided.")
        })

    with open(filepath, "w") as f:
        json.dump(records, f, indent=4)

# Initialize global state
BLACKLIST = load_json_set(BLACKLIST_FILE)
READ_ARTICLES = load_json_set(READ_ARTICLES_FILE)

def analyze_for_stocks(text):
    """Passes extracted text to local Ollama instance to hunt for stock tickers."""
    prompt = f"""You are a financial analyst. Read the following news article and identify any publicly traded companies mentioned. 

Output your response STRICTLY as a JSON list of objects. Do not include any conversational text. Use this exact format:
[
    {{"ticker": "AAPL", "reason": "1-sentence reason why it is mentioned and potential impact"}},
    {{"ticker": "MSFT", "reason": "1-sentence reason why it is mentioned and potential impact"}}
]

If no publicly traded companies are mentioned, output an empty list: []

Article text:
{text}"""
    
    try:
        response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
        raw_output = response.get("response", "").strip()
        
        # Clean up potential markdown formatting (e.g., ```json ... ```)
        cleaned_output = re.sub(r"```[a-zA-Z]*\n|```", "", raw_output).strip()
        
        # Parse the JSON string into a Python list
        tickers_found = json.loads(cleaned_output)
        return tickers_found

    except json.JSONDecodeError:
        logger.error(f"Failed to parse LLM JSON output. Raw output: {raw_output}")
        return "ERROR"
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}")
        return "ERROR"

def process_article(article, output_filepath):
    """Decodes, extracts, and analyzes a single news article, saving to the designated file."""
    decoded = gnewsdecoder(article.link)
    real_link = decoded.get("decoded_url") if decoded.get("status") else article.link

    # Validate URL
    if not real_link or not (real_link.startswith("http://") or real_link.startswith("https://")):
        logger.debug("Skipped: No valid URL available.")
        return False

    # Check if already processed
    if real_link in READ_ARTICLES:
        logger.debug(f"Skipped: Article already read ({article.title}).")
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
        save_json_set(BLACKLIST, BLACKLIST_FILE)
        return False

    extracted_text = trafilatura.extract(downloaded_html)
    
    if not extracted_text:
        logger.debug("Skipped: Could not extract text content.")
        return False

    logger.debug(f"Scanning for potential investments with {OLLAMA_MODEL}...")
    analysis_list = analyze_for_stocks(extracted_text)
    
    if analysis_list == "ERROR":
        return False

    # Check if the list is empty
    if not analysis_list:
        logger.debug("AI Analysis: No actionable stocks found in this article.")
    else:
        # Log the discoveries and save them
        tickers = [item.get("ticker", "UNKNOWN") for item in analysis_list]
        logger.info(f"AI Stock Analysis [{article.source.title}]: Found {', '.join(tickers)}")
        
        save_analysis(article.title, real_link, analysis_list, article.source.title, output_filepath)

    # Mark as read and save state
    READ_ARTICLES.add(real_link)
    save_json_set(READ_ARTICLES, READ_ARTICLES_FILE)

    return True

def fetch_news_for_query(query, header_message, output_filepath, target_articles=2, max_attempts=15):
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
        success = process_article(article, output_filepath)

        if success:
            successful_articles += 1
            time.sleep(random.uniform(1.5, 3.5))

def fetch_discovery_news(target_articles=3):
    """Fetches broad business and tech news to find new stocks."""
    topics = ["emerging technology breakthrough", "business acquisition rumors", "supply chain disruption"]
    
    for topic in topics:
        fetch_news_for_query(
            query=topic, 
            header_message=f"Hunting for stocks in topic: {topic}", 
            output_filepath=DISCOVERIES_FILE, 
            target_articles=target_articles
        )

def fetch_stock_news(target_articles=2):
    """Fetches top financial news for predefined tickers using Google News RSS."""
    logger.debug("Fetching News for Portfolio Tickers")
    
    for ticker in TICKERS:
        query = f"{ticker} stock market"
        fetch_news_for_query(
            query=query, 
            header_message=f"Latest News for {ticker}:", 
            output_filepath=PORTFOLIO_NEWS_FILE, 
            target_articles=target_articles
        )

def scheduled_job():
    """Wrapper function to run all news gathering tasks."""
    logger.debug(f"--- RUNNING SCHEDULED FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    # 1. Look for new stock ideas in general tech/business news (Saves to stock_discoveries.json)
    fetch_discovery_news(target_articles=2)
    
    # 2. Check up on the existing portfolio (Saves to portfolio_news.json)
    fetch_stock_news(target_articles=1)

if __name__ == "__main__":
    scheduled_job()
    schedule.every(60).minutes.do(scheduled_job)
    
    logger.debug("Stock Discovery Scheduler active. Waiting for next job...")
    while True:
        schedule.run_pending()
        time.sleep(1)
