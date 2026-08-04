import logging
import requests
import os
from config_loader import config

logger = logging.getLogger("news_sentinel")

class NewsSentinel:
    """News ingestion and basic sentiment scoring."""
    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY")

    def get_latest_headlines(self, ticker, limit=5):
        """Returns headlines from Polygon News API."""
        try:
            if not self.api_key:
                logger.warning("NEWS_API_KEY missing. News is OFFLINE.")
                return "NEWS_UNAVAILABLE"

            from alpaca.data.historical.news import NewsClient
            from alpaca.data.requests import NewsRequest
            
            client = NewsClient(self.api_key, os.getenv("ALPACA_SECRET_KEY"))
            clean_ticker = ticker.split("=")[0].replace("-", "").upper()
            
            req = NewsRequest(symbols=[clean_ticker], limit=limit)
            news = client.get_news(req)
            
            if not news or not news.news:
                return "NO_NEWS"
            
            headlines = " ".join([n.headline for n in news.news])
            return headlines
        except ImportError:
            logger.error("Alpaca NewsClient not available. Are you using alpaca-py?")
            return "NEWS_UNAVAILABLE"
        except Exception as e:
            logger.error(f"News Fetch Failed: {e}")
            return "NEWS_UNAVAILABLE"

    def audit_news_relevance(self, ticker):
        """Checks headline age using Polygon timestamps."""
        try:
            if not self.api_key:
                return True, "API Key Missing, skipping news relevance check."
                
            from alpaca.data.historical.news import NewsClient
            from alpaca.data.requests import NewsRequest
            
            client = NewsClient(self.api_key, os.getenv("ALPACA_SECRET_KEY"))
            clean_ticker = ticker.split("=")[0].replace("-", "").upper()
            
            req = NewsRequest(symbols=[clean_ticker], limit=1)
            news = client.get_news(req)
            
            if not news or not news.news:
                return True, "No recent news."
            
            pub_utc = news.news[0].created_at
            if not pub_utc:
                return True, "News missing timestamp."
            
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            sim_age_mins = (now - pub_utc).total_seconds() / 60.0
            
            min_age = config.get("trading.min_news_age_minutes", 5.0)
            max_age = config.get("trading.max_news_age_hours", 24.0) * 60
            
            if sim_age_mins < min_age:
                return False, f"HEADLINE TRAP: News is too fresh ({sim_age_mins:.1f}m). HFTs already front-ran this."
            if sim_age_mins > max_age:
                return False, f"STALE NEWS: News is too old ({sim_age_mins/60:.1f}h)."
                
            return True, f"RELEVANT NEWS: Age {sim_age_mins:.1f}m is inside the retail alpha window."
        except Exception as e:
            logger.error(f"Failed to audit news relevance: {e}")
            return True, "Error parsing news."

    def get_sentiment_divergence(self, ticker, price_change_7d):
        """Simple keyword-based headline sentiment scoring."""
        headlines = self.get_latest_headlines(ticker)
        
        # Simplified Sentiment Analysis (In live, use 70B for this)
        sentiment_score = 0.0
        bullish_words = ["bullish", "buy", "growth", "earnings beat", "upgrade"]
        bearish_words = ["bearish", "sell", "investigation", "miss", "downgrade"]
        
        for word in bullish_words:
            if word in headlines.lower(): sentiment_score += 0.2
        for word in bearish_words:
            if word in headlines.lower(): sentiment_score -= 0.2
            
        sentiment_score = max(-1.0, min(1.0, sentiment_score))
        
        # Divergence Logic
        divergence = "NEUTRAL"
        if sentiment_score > 0.3 and price_change_7d < -2.0:
            divergence = "BULLISH_DIVERGENCE"
        elif sentiment_score < -0.3 and price_change_7d > 2.0:
            divergence = "BEARISH_DIVERGENCE"
            
        return {"score": sentiment_score, "type": divergence, "headlines": headlines}
