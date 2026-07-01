import requests
from bs4 import BeautifulSoup
import logging
from local_llm_client import LocalLLMClient
from config_loader import config
from utils import setup_logging

logger = setup_logging("cheap_sentiment")

class CheapSentimentScraper:
    """
    Low-Cost Sentiment Engine.
    Scrapes free financial news sources and uses local Llama 3.1 for analysis.
    Eliminates reliance on expensive paid sentiment APIs.
    """
    def __init__(self):
        self.sources = {
            "forexfactory": "https://www.forexfactory.com/news",
            "investing_forex": "https://www.investing.com/news/forex-news"
        }
        self.local_ai = LocalLLMClient(model="llama3.1")

    def scrape_headlines(self):
        """Scrapes headlines from public sources."""
        headlines = []
        try:
            # Note: In a production environment, use a rotating user-agent
            headers = {"User-Agent": "Mozilla/5.0"}
            
            # Example: ForexFactory Scrape
            res = requests.get(self.sources["forexfactory"], headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                # Simplified selector for the example
                items = soup.find_all("div", class_="flex-1")
                for item in items[:10]:
                    headlines.append(item.text.strip())
        except Exception as e:
            logger.error(f"Scraper error: {e}")
            
        return headlines

    def get_market_bias(self, ticker):
        """Analyzes sentiment using Alpaca News (Primary) and Web Scraper (Fallback)."""
        headlines = []
        
        # 1. Try Alpaca News (Already paid for/included in SIP)
        try:
            from sentiment_sentinel import HarvardConsensusEngine
            sentinel = HarvardConsensusEngine()
            news_data = sentinel._fetch_alpaca_news(ticker)
            if news_data["status"] == "ONLINE":
                headlines = news_data["headlines"]
                logger.info(f"ALPCACA NEWS SYNCED: Found {len(headlines)} headlines.")
        except Exception as e:
            logger.warning(f"Alpaca News fetch failed: {e}")

        # 2. Scraper Fallback (Only if Alpaca is empty)
        if not headlines:
            logger.info("ALPACA NEWS EMPTY. Initiating Web Scraper Fallback...")
            headlines = self.scrape_headlines()

        if not headlines:
            return 0.0, "NEUTRAL (No Data)"
            
        prompt = (
            f"You are a Sentiment Analyst. Based on these headlines, what is the sentiment for {ticker}?\n"
            f"HEADLINES: {headlines[:15]}\n"
            "Output ONLY a number between -1.0 (Very Bearish) and 1.0 (Very Bullish)."
        )
        
        try:
            res = self.local_ai.invoke(prompt)
            bias_score = float(res.content.strip())
            
            status = "NEUTRAL"
            if bias_score > 0.3: status = "BULLISH"
            elif bias_score < -0.3: status = "BEARISH"
            
            return bias_score, status
        except:
            return 0.0, "NEUTRAL (Analysis Error)"

if __name__ == "__main__":
    scraper = CheapSentimentScraper()
    score, status = scraper.get_market_bias("EURUSD")
    print(f"Bias: {score} | Status: {status}")
