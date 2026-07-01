import os
import requests
import logging
from datetime import datetime, timedelta, timezone
from utils import setup_logging
from config_loader import config

logger = setup_logging("pro_sentiment")

class ProSentimentEngine:
    """
    Institutional News Sentiment using Polygon.io.
    Bypasses unreliable scrapers and provides high-res headline analysis.
    """
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
                headlines = [n.get("title", "") for n in news]
                
                # Here we would normally use Llama 3.1 to score these locally!
                # For now, we'll return the count as a proxy for 'Urgency'
                return {
                    "headlines": headlines,
                    "urgency_score": len(headlines) / 10,
                    "status": "ONLINE"
                }
            else:
                logger.error(f"Polygon News API Error: {res.status_code}")
                return {"score": 0.0, "confidence": 0.0, "status": "OFFLINE"}
        except Exception as e:
            logger.error(f"Pro Sentiment Engine failed: {e}")
            return {"score": 0.0, "confidence": 0.0, "status": "ERROR"}

if __name__ == "__main__":
    engine = ProSentimentEngine()
    print(engine.get_asset_sentiment("AAPL"))
