import json
import re

from loguru import logger
import ollama

from stock_news.config import OLLAMA_MODEL


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

        cleaned_output = re.sub(r"```[a-zA-Z]*\n|```", "", raw_output).strip()
        tickers_found = json.loads(cleaned_output)
        return tickers_found

    except json.JSONDecodeError:
        logger.error(
            f"Failed to parse LLM JSON output. Raw output: {raw_output}")
        return "ERROR"
    except Exception as e:
        logger.error(f"Ollama connection failed: {e}")
        return "ERROR"
