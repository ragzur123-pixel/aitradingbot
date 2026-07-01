import os
import numpy as np
import pandas as pd
from utils import setup_logging
from config_loader import config

logger = setup_logging("regime_classifier")

class RegimeClassifier:
    """
    Identifies the 'Market Personality' to switch strategy playbooks.
    Prevents applying Momentum logic in a Mean-Reverting range.
    """
    
    REGIMES = {
        "QUIET_RANGE": "Low Volatility, No Trend. Focus on Mean Reversion at DCL/DCU.",
        "VOLATILE_CHOP": "High Volatility, No Trend. Avoid trading; high fake-out risk.",
        "BULL_MOMENTUM": "Strong Upward Trend. Buy dips, ignore overbought RSI.",
        "BEAR_MOMENTUM": "Strong Downward Trend. Sell rallies, ignore oversold RSI.",
        "CONTROLLED_DRIFT": "Weak Trend with deep retracements. Use wider stops.",
        "PARABOLIC_CHAOS": "Extreme Volatility (3x ATR). Mandatory STAY ASIDE. Non-deterministic state."
    }

    def classify(self, df):
        """Classifies the current market regime based on ADX, ATR, and SMA distance."""
        if df is None or len(df) < 30:
            return "QUIET_RANGE", self.REGIMES["QUIET_RANGE"]

        latest = df.iloc[-1]
        
        # 1. Trend Strength (ADX)
        adx = latest['ADX_14']
        
        # 2. Volatility Trend (ATR relative to its mean)
        historical_atr = df['ATR_14'].tail(50).mean()
        atr_ratio = latest['ATR_14'] / historical_atr if historical_atr > 0 else 1.0
        
        # --- Phase 18: CHAOS VETO (Flash Crash Protection) ---
        if atr_ratio > 3.0:
            res = "PARABOLIC_CHAOS"
            logger.warning(f"CHAOS DETECTED: ATR Ratio is {atr_ratio:.2f}. System Blackout.")
            return res, self.REGIMES[res]
        
        # 3. Directional Alignment
        price_vs_sma = (latest['Close'] - latest['SMA_20']) / latest['SMA_20']
        
        # --- Classification Logic ---
        
        # Strong Momentum
        if adx > 30:
            if price_vs_sma > 0.005: # 0.5% above SMA
                res = "BULL_MOMENTUM"
            elif price_vs_sma < -0.005:
                res = "BEAR_MOMENTUM"
            else:
                res = "CONTROLLED_DRIFT"
        
        # Range / Chop
        else:
            if atr_ratio > 1.5:
                res = "VOLATILE_CHOP"
            else:
                res = "QUIET_RANGE"
                
        logger.info(f"REGIME DETECTED: {res} (ADX: {adx:.2f}, ATR_Ratio: {atr_ratio:.2f})")
        return res, self.REGIMES[res]

if __name__ == "__main__":
    from market_feed import get_live_market_data
    df = get_live_market_data("AAPL")
    clf = RegimeClassifier()
    regime, desc = clf.classify(df)
    print(f"Regime: {regime}\nDescription: {desc}")
