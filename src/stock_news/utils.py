import json
import os
from datetime import datetime

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
