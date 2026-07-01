import pandas as pd
import numpy as np
import logging
from market_feed import get_alpaca_data
from utils import setup_logging
from config_loader import config

logger = setup_logging("fundamental_divergence")

class FundamentalDivergence:
    """
    Operation: Terminal Alpha - Fundamental Divergence 4.0
    Pivoted to 'Quiet Niche' (Dual-Listed / Basis).
    Now detects 'Carry-Leakage' and 'Liquidity Vacuums'.
    """

    # Quiet Niche Mapping (Boring but Stationary)
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
        
        # 1. Fetch Data
        df_p = get_alpaca_data(self.primary_ticker, period_days=lookback_days)
        df_a = get_alpaca_data(self.anchor_ticker, period_days=lookback_days)
        
        import yfinance as yf
        df_fx = yf.download(self.fx_ticker, period=f"{lookback_days}d", interval="1d", progress=False)
        df_rate = yf.download(self.rate_ticker, period=f"{lookback_days}d", interval="1d", progress=False)

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
        us_rate = yf.download("^TNX", period="1d", progress=False)['Close'].iloc[-1]
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
            # VETO: Liquidity Vacuum (Low relative volume during divergence)
            if curr_vol_z < -1.5:
                signal = "LIQUIDITY_VETO"
                risk_flags.append(f"Liquidity Vacuum: Volume Z-score is {curr_vol_z:.2f}")
            
            # VETO: Excessive Carry Leakage (> 3% yield spread)
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
