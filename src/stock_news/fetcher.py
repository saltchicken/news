import urllib.parse
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests
from googlenewsdecoder import gnewsdecoder
from loguru import logger
from playwright.sync_api import sync_playwright
import trafilatura

from stock_news.config import READ_ARTICLES_FILE
from stock_news.utils import load_json_set, save_json_set, save_analysis
from stock_news.analyzer import analyze_for_stocks

# Initialize global state for the fetcher
READ_ARTICLES = load_json_set(READ_ARTICLES_FILE)

def fetch_tier_1_curl(url):
    """Tier 1: High-speed request mimicking a standard Chrome browser TLS fingerprint."""
    try:
        response = curl_requests.get(url, impersonate="chrome", timeout=15)
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
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
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
    real_link = decoded.get("decoded_url") if decoded.get("status") else article.link

    if not real_link or not (real_link.startswith("http://") or real_link.startswith("https://")):
        return False

    if real_link in READ_ARTICLES:
        return False

    domain = urllib.parse.urlparse(real_link).netloc
    logger.debug(f"Processing: {article.title[:50]}... | {domain}")

    downloaded_html = fetch_tier_1_curl(real_link)

    if not downloaded_html:
        logger.debug(f"Escalating to Tier 2 (Playwright) for {domain}...")
        downloaded_html = fetch_tier_2_playwright(real_link)

    extracted_text = None
    if downloaded_html:
        extracted_text = trafilatura.extract(downloaded_html)

    if not extracted_text:
        logger.warning(f"Tiers 1 & 2 failed for {domain}. Engaging Tier 3 RSS Failsafe.")
        raw_summary = getattr(article, "summary", "") or getattr(article, "description", "")
        extracted_text = clean_rss_summary(raw_summary)

        if not extracted_text or len(extracted_text) < 100:
            logger.warning(f"Complete failure. Skipping '{domain}'.")
            return False

    analysis_list = analyze_for_stocks(extracted_text)

    if analysis_list == "ERROR":
        return False

    if not analysis_list:
        logger.debug("AI Analysis: No actionable stocks found in this article.")
    else:
        tickers = [item.get("ticker", "UNKNOWN") for item in analysis_list]
        logger.info(f"AI Analysis [{article.source.title}]: Found {', '.join(tickers)}")
        save_analysis(article.title, real_link, analysis_list, article.source.title, output_filepath)

    READ_ARTICLES.add(real_link)
    save_json_set(READ_ARTICLES, READ_ARTICLES_FILE)

    return True
