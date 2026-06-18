from datetime import datetime
from datetime import timedelta
import sqlite3

from loguru import logger

from stock_news.config import DB_FILE


def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():
    """Initializes the SQLite database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS read_articles (
                url TEXT PRIMARY KEY
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discoveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                source TEXT,
                title TEXT,
                link TEXT,
                ticker TEXT,
                sentiment TEXT,
                analysis TEXT,
                topic TEXT
            )
        ''')
        conn.commit()


def is_article_read(url):
    """Checks if an article has already been processed."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM read_articles WHERE url = ?", (url,))
        return cursor.fetchone() is not None


def mark_article_read(url):
    """Marks an article as processed."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO read_articles (url) VALUES (?)",
                       (url,))
        conn.commit()


def save_analysis(article_title, article_link, ticker_data, source, topic):
    """Saves AI ticker analysis to the SQLite database."""
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        for item in ticker_data:
            cursor.execute(
                '''
                INSERT INTO discoveries (timestamp, source, title, link, ticker, sentiment, analysis, topic)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, source, article_title, article_link,
                  item.get("ticker", "UNKNOWN"), item.get(
                      "sentiment",
                      "Neutral"), item.get("reason", "No reason provided."), topic))
        conn.commit()


def print_recent_findings(hours=24, sentiment=None):
    """Prints findings from the past specified hours, optionally filtered by sentiment."""
    timeframe_start = (datetime.now() - timedelta(hours=hours)).isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()
        if sentiment:
            cursor.execute(
                '''
                SELECT timestamp, ticker, sentiment, title, link, analysis, topic
                FROM discoveries
                WHERE timestamp >= ? AND LOWER(sentiment) = LOWER(?)
                ORDER BY timestamp DESC
            ''', (timeframe_start, sentiment))
        else:
            cursor.execute(
                '''
                SELECT timestamp, ticker, sentiment, title, link, analysis, topic
                FROM discoveries
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            ''', (timeframe_start,))
        rows = cursor.fetchall()

    logger.info(f"=== FINDINGS FROM THE PAST {hours} HOURS ===")
    if not rows:
        logger.info(f"No findings recorded in the past {hours} hours.")
        return

    for row in rows:
        timestamp, ticker, sentiment, title, link, analysis, topic = row
        logger.info(f"{ticker}")
        logger.info(f"   Topic: {topic}")
        logger.info(f"   Sentiment: {sentiment}")
        logger.info(f"   Title: {title}")
        logger.info(f"   Link: {link}")
        logger.info(f"   Analysis: {analysis}")
