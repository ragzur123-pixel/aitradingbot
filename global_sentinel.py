"""Global macro veto based on lead-lag relationships."""
import yfinance as yf
import logging
from utils import setup_logging
from config_loader import config

logger = setup_logging("global_sentinel")

from pro_data_bridge import ProDataBridge

class GlobalSentinel:
    """Global macro veto based on lead-lag relationships."""
    def __init__(self):
        self.pro_bridge = ProDataBridge()

    def get_macro_weather(self):
        """Fetches current state of global lead assets."""
        weather = {}
        leads = {
            "DXY": "DX-Y.NYB",
            "VIX": "^VIX",
            "US10Y": "^TNX",
            "EURUSD": "EURUSD=X"
        }
        
        for name, ticker in leads.items():
            # 1. Try Polygon (Primary)
            df = self.pro_bridge.get_macro_data(ticker)
            
            # 2. Try yfinance (Fallback)
            if df is None or df.empty:
                logger.info(f"Polygon failed for {name}. Falling back to yfinance.")
                try:
                    df = yf.download(ticker, period="2d", interval="1h", progress=False)
                except Exception as e: 
                    logger.error(f"FATAL: Macro data fetch failed for {name}: {e}")
                    raise ConnectionError(f"Macro data unavailable for {name}")

            if df is not None and not df.empty:
                if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
                    df.columns = df.columns.get_level_values(0)
                try:
                    latest = float(df['Close'].iloc[-1])
                    prev = float(df['Close'].iloc[-5]) if len(df) >= 5 else latest
                    change = (latest - prev) / prev
                    weather[name] = {"price": latest, "5h_change": change}
                except Exception as e:
                    logger.error(f"Failed to parse macro data for {name}: {e}")
                    raise
        
        return weather

    def check_global_veto(self, ticker, direction):
        """
        Provides a 'Macro Veto' based on lead-lag relationships.
        Example: VETO 'Long' on EURUSD if DXY is > 0.5% in 5 hours.
        """
        weather = self.get_macro_weather()
        if not weather: return False, "SENSORS_OFFLINE"

        dxy_move = weather.get("DXY", {}).get("5h_change", 0)
        vix_price = weather.get("VIX", {}).get("price", 20)

        # 1. RISK-OFF VETO (VIX)
        vix_threshold = config.get("trading.vix_veto_threshold", 30.0)
        if vix_price > vix_threshold and direction == "LONG":
            return True, f"GLOBAL_PANIC: VIX > {vix_threshold}. Risk-Off Veto active."

        # 2. DOLLAR STRENGTH VETO
        # If DXY is pumping (>0.5% in 5h), VETO any trade against the dollar
        is_against_usd = ("EURUSD" in ticker or "GBPUSD" in ticker or "AUDUSD" in ticker)
        if dxy_move > 0.005 and is_against_usd and direction == "LONG":
            return True, f"DXY_PARABOLIC: Dollar Index up {dxy_move:.2%}. Vetoing counter-trend Long."

        # 3. YIELD SPIKE VETO (Gold/Nasdaq)
        yield_move = weather.get("US10Y", {}).get("5h_change", 0)
        if yield_move > 0.02 and (ticker == "XAUUSD" or ticker == "NQ") and direction == "LONG":
            return True, f"YIELD_SPIKE: 10Y Yields up {yield_move:.2%}. Vetoing Long on Interest-Sensitive assets."

        return False, "CLEAR"

if __name__ == "__main__":
    sentinel = GlobalSentinel()
    is_veto, reason = sentinel.check_global_veto("EURUSD=X", "LONG")
    print(f"Veto: {is_veto} | Reason: {reason}")
