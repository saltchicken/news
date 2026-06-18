import sqlite3
from datetime import datetime

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
                analysis TEXT
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
        cursor.execute("INSERT OR IGNORE INTO read_articles (url) VALUES (?)", (url,))
        conn.commit()

def save_analysis(article_title, article_link, ticker_data, source):
    """Saves AI ticker analysis to the SQLite database."""
    timestamp = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        for item in ticker_data:
            cursor.execute('''
                INSERT INTO discoveries (timestamp, source, title, link, ticker, sentiment, analysis)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                source,
                article_title,
                article_link,
                item.get("ticker", "UNKNOWN"),
                item.get("sentiment", "Neutral"),
                item.get("reason", "No reason provided.")
            ))
        conn.commit()
