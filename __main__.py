from datetime import datetime
import json
import os
import random
import re
import sys
import time
import urllib.parse

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
import feedparser
from googlenewsdecoder import gnewsdecoder
from loguru import logger
import ollama
from playwright.sync_api import sync_playwright
import schedule
import trafilatura

# Configuration
OLLAMA_MODEL = "gemma4:e4b"
BLACKLIST_FILE = "domain_blacklist.json"
READ_ARTICLES_FILE = "read_articles.json"
DISCOVERIES_FILE = "stock_discoveries.json"

# Configure Loguru
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
    format=
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
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
            "sentiment": item.get("sentiment", "Neutral"),
            "analysis": item.get("reason", "No reason provided.")
        })

    with open(filepath, "w") as f:
        json.dump(records, f, indent=4)


# Initialize global state
BLACKLIST = load_json_set(BLACKLIST_FILE)
READ_ARTICLES = load_json_set(READ_ARTICLES_FILE)


def analyze_for_stocks(text):
    """Passes extracted text to local Ollama instance to hunt for stock tickers and analyze sentiment."""
    prompt = f"""You are a financial analyst. Read the following news article and identify any publicly traded companies mentioned. 

Output your response STRICTLY as a JSON list of objects. Do not include any conversational text. Use this exact format:
[
    {{"ticker": "AAPL", "sentiment": "Positive", "reason": "1-sentence reason why it is mentioned and potential impact"}},
    {{"ticker": "MSFT", "sentiment": "Negative", "reason": "1-sentence reason why it is mentioned and potential impact"}}
]

The "sentiment" field MUST be exactly one of: "Positive", "Negative", or "Neutral".

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
        logger.error(
            f"Failed to parse LLM JSON output. Raw output: {raw_output}")
        return "ERROR"
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}")
        return "ERROR"


def fetch_tier_1_curl(url):
    """Tier 1: High-speed request mimicking a standard Chrome browser TLS fingerprint."""
    try:
        response = curl_requests.get(url, impersonate="chrome", timeout=15)
        # 403 Forbidden and 401 Unauthorized are standard bot-blocks
        if response.status_code in [200, 201, 202]:
            return response.text
        logger.debug(f"Tier 1 failed with status code: {response.status_code}")
        return None
    except Exception as e:
        logger.debug(f"Tier 1 exception: {e}")
        return None


def fetch_tier_2_playwright(url):
    """Tier 2: Headless browser to render JavaScript and bypass moderate protections."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            # Wait until the DOM is loaded, no need to wait for every tracking script
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.debug(f"Tier 2 Playwright failed: {e}")
        return None


def clean_rss_summary(html_content):
    """Utility to extract clean text from messy RSS summary payloads."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def process_article(article, output_filepath):
    """Decodes, extracts, and analyzes a single news article through a tiered fetching system."""
    decoded = gnewsdecoder(article.link)
    real_link = decoded.get("decoded_url") if decoded.get(
        "status") else article.link

    if not real_link or not (real_link.startswith("http://") or
                             real_link.startswith("https://")):
        return False

    if real_link in READ_ARTICLES:
        return False

    domain = urllib.parse.urlparse(real_link).netloc

    if domain in BLACKLIST:
        logger.debug(f"Skipped: Domain '{domain}' is blacklisted.")
        return False

    logger.debug(f"Processing: {article.title[:50]}... | {domain}")

    # --- THE WATERFALL FETCHING SYSTEM ---

    downloaded_html = None
    extracted_text = None

    # Tier 1: curl_cffi
    downloaded_html = fetch_tier_1_curl(real_link)

    # Tier 2: Playwright Escalation
    if not downloaded_html:
        logger.debug(f"Escalating to Tier 2 (Playwright) for {domain}...")
        downloaded_html = fetch_tier_2_playwright(real_link)

    # Attempt Text Extraction if HTML was acquired
    if downloaded_html:
        extracted_text = trafilatura.extract(downloaded_html)

    # Tier 3: RSS Summary Failsafe
    if not extracted_text:
        logger.warning(
            f"Tiers 1 & 2 failed for {domain}. Engaging Tier 3 RSS Failsafe.")
        raw_summary = getattr(article, "summary", "") or getattr(
            article, "description", "")
        extracted_text = clean_rss_summary(raw_summary)

        # If even the failsafe yields practically nothing, only then do we blacklist
        if not extracted_text or len(extracted_text) < 100:
            logger.warning(f"Complete failure. Blacklisting '{domain}'.")
            BLACKLIST.add(domain)
            save_json_set(BLACKLIST, BLACKLIST_FILE)
            return False

    # --- PROCEED WITH AI ANALYSIS ---

    analysis_list = analyze_for_stocks(extracted_text)

    if analysis_list == "ERROR":
        return False

    if not analysis_list:
        logger.debug("AI Analysis: No actionable stocks found in this article.")
    else:
        tickers = [item.get("ticker", "UNKNOWN") for item in analysis_list]
        logger.info(
            f"AI Analysis [{article.source.title}]: Found {', '.join(tickers)}")
        save_analysis(article.title, real_link, analysis_list,
                      article.source.title, output_filepath)

    READ_ARTICLES.add(real_link)
    save_json_set(READ_ARTICLES, READ_ARTICLES_FILE)

    return True


def fetch_news_for_query(query,
                         header_message,
                         output_filepath,
                         timeframe="1h"):
    """Fetches Google News RSS for a query and processes all articles found within the timeframe."""
    logger.debug(header_message)

    # Append the time constraint to the query to force recent articles
    recent_query = f"{query} when:{timeframe}"
    encoded_topic = urllib.parse.quote_plus(recent_query)

    url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)

    for article in feed.entries:
        success = process_article(article, output_filepath)

        if success:
            time.sleep(random.uniform(1.5, 3.5))


def fetch_discovery_news():
    """Fetches broad business and tech news to find new stocks."""
    topics = [
        "emerging technology breakthrough", "business acquisition rumors",
        "supply chain disruption"
    ]

    for topic in topics:
        fetch_news_for_query(
            query=topic,
            header_message=f"Hunting for stocks in topic: {topic}",
            output_filepath=DISCOVERIES_FILE)


def scheduled_job():
    """Wrapper function to run all news gathering tasks."""
    logger.debug(
        f"--- RUNNING SCHEDULED FETCH: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
    )

    # Look for new stock ideas in general tech/business news (Saves to stock_discoveries.json)
    fetch_discovery_news()


if __name__ == "__main__":
    scheduled_job()
    schedule.every(60).minutes.do(scheduled_job)

    logger.debug("Stock Discovery Scheduler active. Waiting for next job...")
    while True:
        schedule.run_pending()
        time.sleep(1)
