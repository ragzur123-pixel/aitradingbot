import pandas as pd
import numpy as np
import logging
from market_feed import get_alpaca_data
from utils import setup_logging
from config_loader import config

logger = setup_logging("fundamental_divergence")

class FundamentalDivergence:
    """Analyzes basis divergence between asset and anchor."""

    # Asset Mapping
    NICHE_MAP = {
        "GOLD": {"anchor": "GDX", "currency": "USDCAD=X", "local_rate_proxy": "^IRX"}, # Barrick (Dual)
        "BHP": {"anchor": "PICK", "currency": "USDAUD=X", "local_rate_proxy": "^TNX"}, # BHP ADR
        "RIO": {"anchor": "PICK", "currency": "USDAUD=X", "local_rate_proxy": "^TNX"}, # Rio ADR
        "AEM": {"anchor": "GDX", "currency": "USDCAD=X", "local_rate_proxy": "^IRX"}  # Agnico (Dual)
    }

    def __init__(self, primary_ticker="GOLD", anchor_ticker="GDX"):
        self.primary_ticker = primary_ticker
        self.anchor_ticker = anchor_ticker
        niche = self.NICHE_MAP.get(primary_ticker, {"currency": "DX-Y.NYB", "local_rate_proxy": "^TNX"})
        self.fx_ticker = niche["currency"]
        self.rate_ticker = niche["local_rate_proxy"]

    def analyze(self, lookback_days=60):
        logger.info(f"Analyzing Quiet Niche: {self.primary_ticker} vs {self.anchor_ticker}")
        
        from market_feed import get_live_market_data
        
        # 1. Fetch Data
        df_p = get_live_market_data(self.primary_ticker, period=f"{lookback_days}d", interval="1d")
        df_a = get_live_market_data(self.anchor_ticker, period=f"{lookback_days}d", interval="1d")
        
        df_fx = get_live_market_data(self.fx_ticker, period=f"{lookback_days}d", interval="1d")
        df_rate = get_live_market_data(self.rate_ticker, period=f"{lookback_days}d", interval="1d")

        if any(d is None or d.empty for d in [df_p, df_a, df_fx, df_rate]):
            logger.error("Divergence Ingestion Failed.")
            return None

        # 2. Align Data
        combined = pd.DataFrame({
            'primary': df_p['Close'],
            'anchor': df_a['Close'],
            'fx': df_fx['Close'],
            'rate': df_rate['Close'],
            'p_vol': df_p['Volume']
        }).dropna()

        # 3. Calculate Divergence & Carry Leakage
        combined['ratio'] = combined['primary'] / combined['anchor']
        
        # Carry-Leakage: If local rate > US rate, holding ADR long has negative carry
        df_us_rate = get_live_market_data("^TNX", period="5d", interval="1d")
        us_rate = df_us_rate['Close'].iloc[-1] if (df_us_rate is not None and not df_us_rate.empty) else 0.0
        local_rate = combined['rate'].iloc[-1]
        carry_risk = local_rate - us_rate # Spread in yield
        
        # 4. Liquidity Guard (Volume z-score)
        vol_mean = combined['p_vol'].rolling(window=20).mean()
        vol_std = combined['p_vol'].rolling(window=20).std()
        vol_z = (combined['p_vol'] - vol_mean) / vol_std
        curr_vol_z = vol_z.iloc[-1]
        
        # 5. Z-Score logic
        mean_ratio = combined['ratio'].mean()
        std_ratio = combined['ratio'].std()
        z_score = (combined['ratio'].iloc[-1] - mean_ratio) / std_ratio

        signal = "NEUTRAL"
        risk_flags = []

        if abs(z_score) > 3.0:
            # Veto: Low volume
            if curr_vol_z < -1.5:
                signal = "LIQUIDITY_VETO"
                risk_flags.append(f"Liquidity Vacuum: Volume Z-score is {curr_vol_z:.2f}")
            
            # Veto: High rate spread
            elif carry_risk > 3.0:
                signal = "CARRY_VETO"
                risk_flags.append(f"Negative Carry: Rate spread is {carry_risk:.2f}%")
            
            else:
                signal = "QUIET_ALPHA_CANDIDATE"

        return {
            "tickers": f"{self.primary_ticker}/{self.anchor_ticker}",
            "z_score": round(z_score, 2),
            "carry_risk": round(carry_risk, 2),
            "vol_z": round(curr_vol_z, 2),
            "signal": signal,
            "risk_flags": risk_flags
        }

if __name__ == "__main__":
    divergence = FundamentalDivergence()
    result = divergence.analyze()
    if result:
        print(f"--- Divergence Report ---\n{result}")
