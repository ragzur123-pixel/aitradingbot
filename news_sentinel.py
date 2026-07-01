import logging
import requests
import os
import json
from config_loader import config

logger = logging.getLogger("news_sentinel")

class NewsSentinel:
    """
    Real-Time News Ingestion.
    Captures Fundamental Catalysts (Earnings, SEC, Macro).
    """
    def __init__(self):
        # Using a free Financial News API or RSS fallback
        self.api_key = os.getenv("NEWS_API_KEY") 

    def get_latest_headlines(self, ticker, limit=5):
        """Fetches recent news for a specific asset."""
        try:
            # Fallback to a public RSS/Scraper or NewsAPI
            # For this 'Zero-Cost' implementation, we simulate news-wires
            # In live, replace with Bloomberg/Reuters/Polygon News API
            
            # Placeholder for Actual Ingestion
            headlines = [
                f"NEWS for {ticker}: No significant fundamental breaks in the last 24h.",
                f"MACRO: Fed comments expected to remain hawkish.",
                f"LIQUIDITY: Global liquidity index shows stable expansion."
            ]
            
            return "\n".join(headlines[:limit])
        except Exception as e:
            logger.error(f"News Fetch Failed: {e}")
            return "NEWS_UNAVAILABLE"

    def audit_news_relevance(self, ticker):
        """
        News Staleness Veto.
        - If News is < 5 mins old: REJECT (Likely already priced in by HFTs).
        - If News is > 24 hours old: REJECT (Stale).
        - Targeted Age: 15 mins to 4 hours (The 'Retail Sentiment' window).
        """
        # Placeholder for real timestamped news processing
        # In a real feed, headlines would have accurate 'published_at' times.
        import random
        sim_age_mins = random.uniform(0, 1440) # Simulate random headline age
        
        min_age = config.get("trading.min_news_age_minutes", 5.0)
        max_age = config.get("trading.max_news_age_hours", 24.0) * 60
        
        if sim_age_mins < min_age:
            return False, f"HEADLINE TRAP: News is too fresh ({sim_age_mins:.1f}m). HFTs already front-ran this."
        if sim_age_mins > max_age:
            return False, f"STALE NEWS: News is too old ({sim_age_mins/60:.1f}h)."
            
        return True, f"RELEVANT NEWS: Age {sim_age_mins:.1f}m is inside the retail alpha window."

    def get_sentiment_divergence(self, ticker, price_change_7d):
        """
        Detects Information Asymmetry.
        Sentiment Score (-1 to 1) vs. Price Change.
        If News is BULLISH (+0.5) but Price is DOWN (-5%), this is a BULLISH DIVERGENCE (Leading).
        """
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
