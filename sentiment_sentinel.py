import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest
from alpaca.data.live import NewsDataStream
from langchain_google_genai import ChatGoogleGenerativeAI
from token_tracker import track_token_usage
from config_loader import config
from utils import setup_logging

load_dotenv()
logger = setup_logging("sentiment_sentinel")

SENTIMENT_FILE = "last_valid_bias.json"

class HarvardConsensusEngine:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        if self.api_key and self.secret_key:
            self.news_client = NewsClient(self.api_key, self.secret_key)
            self.stream_client = NewsDataStream(self.api_key, self.secret_key)
        else:
            self.news_client = None
            self.stream_client = None
            logger.warning("Alpaca keys missing. News sentiment will be offline.")

        # Phase 2: High-Speed NLP with Gemini 1.5 Flash
        junior_cfg = config.get("models.junior_analyst", {"name": "gemini-1.5-flash", "temperature": 0})
        self.llm = ChatGoogleGenerativeAI(model=junior_cfg["name"], temperature=junior_cfg["temperature"])
        self.current_ticker = "EURUSD=X"

    async def _on_news(self, news):
        """Callback for real-time news stream."""
        logger.info(f"LIVE NEWS RECEIVED: {news.headline}")
        
        # Analyze immediately
        prompt = (
            "You are a Senior Macro Sentiment Analyst. Analyze this headline for its immediate IMPACT on the asset price.\n"
            "Output ONLY a single numeric score between -1.0 (Extremely Bearish) and 1.0 (Extremely Bullish).\n\n"
            f"HEADLINE: {news.headline}\n"
            f"SUMMARY: {news.summary if news.summary else 'N/A'}"
        )
        
        try:
            res = self.llm.invoke(prompt)
            score = self.validate_bias(res.content.strip())
            if hasattr(res, 'usage_metadata'):
                track_token_usage(res.usage_metadata.input_token_count, res.usage_metadata.output_token_count, model="gemini-1.5-flash")
            
            logger.info(f"LIVE SENTIMENT SCORE: {score} for {self.current_ticker}")
            
            # Update the global bias file instantly
            self.run_sentinel(self.current_ticker, override_news_bias=score)
        except Exception as e:
            logger.error(f"Live Sentiment Analysis failed: {e}")

    async def start_live_ingestion(self, ticker):
        """Starts a persistent WebSocket listener for news."""
        if not self.stream_client:
            logger.error("Cannot start live ingestion without Alpaca keys.")
            return

        self.current_ticker = ticker
        from market_feed import get_alpaca_symbol
        symbol, _ = get_alpaca_symbol(ticker)
        
        logger.info(f"Subscribing to LIVE news for {symbol}...")
        self.stream_client.subscribe_news(self._on_news, symbol)
        
        # This is a blocking call
        await self.stream_client._run_forever()

    def _fetch_alpaca_news(self, ticker):
        """Fetch real-time news headlines using Alpaca News API."""
        if not self.news_client:
            return {"source": "Alpaca_News", "headlines": [], "status": "OFFLINE"}

        try:
            # Clean ticker for Alpaca (e.g., AAPL, BTC/USD)
            from market_feed import get_alpaca_symbol
            symbol, _ = get_alpaca_symbol(ticker)
            
            # Look back 2 hours for leading sentiment
            start_time = datetime.now(timezone.utc) - timedelta(hours=2)
            
            request_params = NewsRequest(
                symbols=[symbol],
                start=start_time,
                limit=10
            )
            
            news = self.news_client.get_news(request_params)
            headlines = [n.headline for n in news.news]
            
            return {
                "source": "Alpaca_News", 
                "headlines": headlines, 
                "status": "ONLINE" if headlines else "ONLINE_EMPTY"
            }
        except Exception as e:
            logger.warning(f"Alpaca News Fetch failed for {ticker}: {e}")
            return {"source": "Alpaca_News", "headlines": [], "status": "OFFLINE"}

    def _fetch_retail_ratios(self, ticker):
        """Fetch retail positioning from DailyFX (Still useful for contrarian views)."""
        url = "https://content.dailyfx.com/api/v1/sentiment"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                clean_ticker = ticker.replace("=X", "").replace("-USD", "").replace("/", "").upper()
                for item in data.get("dailyfx_sentiment", []):
                    item_symbol = item.get("symbol", "").replace("/", "").upper()
                    if clean_ticker in item_symbol:
                        long_pct = float(item.get("long_pct", 50)) / 100
                        return {"source": "DailyFX_Retail", "long_pct": long_pct, "short_pct": 1 - long_pct, "status": "ONLINE"}
        except Exception as e:
            logger.warning(f"DailyFX Sentiment API failed: {e}")
        
        return {"source": "Retail_Broker", "long_pct": 0.5, "short_pct": 0.5, "status": "OFFLINE"}

    def validate_bias(self, bias):
        """Strict schema validation for bias scores."""
        try:
            val = float(bias)
            return max(-1.0, min(1.0, val))
        except:
            return 0.0

    def analyze_anonymous_votes(self, data_sources):
        """Applies Harvard weighting and independent evaluation."""
        votes = []
        
        # Vote 1: Retail (Contrarian)
        retail = data_sources.get("retail")
        if retail and retail["status"] == "ONLINE":
            raw_bias = 0.0
            if retail["long_pct"] > 0.70: raw_bias = -1.0 # Contrarian Sell
            elif retail["short_pct"] > 0.70: raw_bias = 1.0 # Contrarian Buy
            votes.append({"source": "Retail_Contrarian", "bias": raw_bias, "weight": 1.0})
            
        # Vote 2: News Headlines (Gemini 1.5 Flash Scored)
        news = data_sources.get("news")
        if news and "ONLINE" in news["status"] and news["headlines"]:
            headlines_str = "\n".join(news["headlines"])
            prompt = (
                "You are a Senior Macro Sentiment Analyst. Analyze these headlines for their immediate IMPACT on the asset price.\n"
                "Output ONLY a single numeric score between -1.0 (Extremely Bearish) and 1.0 (Extremely Bullish).\n\n"
                f"HEADLINES:\n{headlines_str}"
            )
            try:
                res = self.llm.invoke(prompt)
                score = self.validate_bias(res.content.strip())
                if hasattr(res, 'usage_metadata'):
                    track_token_usage(res.usage_metadata.input_token_count, res.usage_metadata.output_token_count, model="gemini-1.5-flash")
                votes.append({"source": "News_Gemini_Flash", "bias": score, "weight": 1.2})
            except Exception as e:
                logger.error(f"Gemini Sentiment Analysis failed: {e}")

        return votes

    def calculate_trimmed_mean(self, votes):
        if not votes: return 0.0
        total_w = sum(v["weight"] for v in votes)
        return sum(v["bias"] * v["weight"] for v in votes) / total_w if total_w > 0 else 0.0

    def run_sentinel(self, ticker, override_news_bias=None):
        logger.info(f"--- Running Sentinel Logic for {ticker} ---")
        
        sources = {
            "retail": self._fetch_retail_ratios(ticker),
            "news": self._fetch_alpaca_news(ticker) if override_news_bias is None else {"source": "Live_News", "status": "ONLINE", "headlines": ["Live Stream"]}
        }
        
        votes = self.analyze_anonymous_votes(sources)
        
        # If we have an override (from WebSocket), replace/add it
        if override_news_bias is not None:
            # Clear existing news votes
            votes = [v for v in votes if "News" not in v["source"]]
            votes.append({"source": "News_Live_WebSocket", "bias": override_news_bias, "weight": 1.5})
            
        aggregated_bias = self.calculate_trimmed_mean(votes)
        
        online_count = sum(1 for s in sources.values() if "ONLINE" in s.get("status", ""))
        
        # Reliability Fail-Safe (Phase 18 Hardening)
        # 2+ sources = high, 1 source = med, 0 = blind
        confidence_score = 0.90 if online_count >= 2 else 0.50 if online_count == 1 else 0.10
        
        if online_count == 0:
            aggregated_bias = 0.0 # Neutralize bias if blind
        
        retail_long = sources["retail"].get("long_pct", 0.5)
        herd_status = "STABLE"
        if retail_long > 0.75: herd_status = "EXTREME_RETAIL_BULLISH (TRAP)"
        elif retail_long < 0.25: herd_status = "EXTREME_RETAIL_BEARISH (SQUEEZE)"
        
        final_thesis = {
            "ticker": ticker,
            "timestamp": int(time.time()),
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "aggregated_bias": round(aggregated_bias, 3),
            "confidence": confidence_score,
            "herd_status": herd_status,
            "sources_online": online_count,
            "headlines_analyzed": len(sources["news"].get("headlines", []))
        }

        self._save_state(final_thesis)
        logger.info(f"Sentinel Final: Bias={final_thesis['aggregated_bias']} | Confidence={confidence_score}")
        return final_thesis

    def _save_state(self, data):
        temp_path = SENTIMENT_FILE + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=4)
        os.replace(temp_path, SENTIMENT_FILE)

if __name__ == "__main__":
    sentinel = HarvardConsensusEngine()
    sentinel.run_sentinel("EURUSD=X")
