import os
import requests
import logging
import pandas as pd
from datetime import datetime, timedelta, timezone
from utils import setup_logging

logger = setup_logging("pro_data_bridge")

class ProDataBridge:
    """
    Professional Data Feed (Polygon.io).
    Eliminates 'Toy Data' foundation (yfinance) for macro leads.
    """
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY")
        self.base_url = "https://api.polygon.io"

    def get_macro_data(self, ticker, days=5):
        """Fetch professional-grade OHLCV from Polygon."""
        if not self.api_key:
            logger.warning("POLYGON_API_KEY missing. Professional data bridge is offline.")
            return None

        # Polygon Ticker Translation (e.g., C:EURUSD)
        poly_ticker = ticker
        if "EURUSD" in ticker: poly_ticker = "C:EURUSD"
        if "AAPL" in ticker: poly_ticker = "AAPL"
        
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/v2/aggs/ticker/{poly_ticker}/range/1/hour/{start}/{end}?apiKey={self.api_key}"
        
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json().get("results", [])
                if not data: return None
                
                df = pd.DataFrame(data)
                df['Date'] = pd.to_datetime(df['t'], unit='ms')
                df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
                return df.set_index('Date')
            else:
                logger.error(f"Polygon API Error: {res.status_code}")
                return None
        except Exception as e:
            logger.error(f"Polygon bridge failed: {e}")
            return None

if __name__ == "__main__":
    bridge = ProDataBridge()
    df = bridge.get_macro_data("EURUSD")
    if df is not None: print(df.tail())
