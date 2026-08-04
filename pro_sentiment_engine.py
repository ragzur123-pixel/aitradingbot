import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from utils import setup_logging
from config_loader import config

logger = setup_logging("pro_sentiment")

class ProSentimentEngine:
    """Polygon.io news sentiment stub."""
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY")
        self.base_url = "https://api.polygon.io/v2/reference/news"

    def get_asset_sentiment(self, ticker):
        """Fetches and analyzes recent headlines for a specific ticker."""
        if not self.api_key:
            logger.warning("POLYGON_API_KEY missing. Pro Sentiment is OFFLINE.")
            return {"score": 0.0, "confidence": 0.0}

        # Clean ticker
        clean_ticker = ticker.split("=")[0].replace("-", "").upper()
        
        params = {
            "ticker": clean_ticker,
            "limit": 10,
            "apiKey": self.api_key
        }

        try:
            res = requests.get(self.base_url, params=params, timeout=10)
            if res.status_code == 200:
                news = res.json().get("results", [])
                if not news: return {"score": 0.0, "confidence": 0.1}

                # High-res logic: analyze headlines + summaries
                headlines_str = " ".join([n.get("title", "") for n in news])
                
                try:
                    from local_llm_client import LocalLLMClient
                    llm = LocalLLMClient()
                    prompt = f"Analyze these news headlines for {clean_ticker} and provide a sentiment score from -1.0 (very bearish) to 1.0 (very bullish). Only output the float number.\n\nHeadlines:\n{headlines_str}"
                    res_llm = llm.invoke(prompt)
                    score_str = res_llm.content.strip()
                    # Try to parse the float securely
                    import re
                    match = re.search(r"[-+]?\d*\.\d+|\d+", score_str)
                    if match:
                        score = float(match.group(0))
                        # Clamp between -1.0 and 1.0
                        score = max(-1.0, min(1.0, score))
                    else:
                        score = 0.0
                        
                    return {"score": score, "confidence": 0.8, "status": "LLM_SCORED"}
                except Exception as e:
                    logger.error(f"Local Llama sentiment scoring failed: {e}")
                    return {"score": 0.0, "confidence": 0.1, "status": "LLM_FAILED"}
            else:
                logger.error(f"Polygon News API Error: {res.status_code}")
                return {"score": 0.0, "confidence": 0.0, "status": "OFFLINE"}
        except Exception as e:
            logger.error(f"Pro Sentiment Engine failed: {e}")
            return {"score": 0.0, "confidence": 0.0, "status": "ERROR"}

if __name__ == "__main__":
    engine = ProSentimentEngine()
    print(engine.get_asset_sentiment("AAPL"))
