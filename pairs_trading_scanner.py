import pandas as pd
import numpy as np
import logging
from indicators import calculate_zscore, calculate_beta
from market_feed import get_live_market_data
from utils import setup_logging
from config_loader import config

logger = setup_logging("arbitrage_engine")

class CorrelationArbitrageEngine:
    """
    Statistical Arbitrage Engine.
    Trades the 'Error' between two highly correlated assets.
    Edge: Mean Reversion of the Spread.
    """
    def __init__(self):
        self.lookback = 60
        self.z_threshold = config.get("trading.min_zscore_anomaly", 3.0)

    def get_spread_zscore(self, asset_a_df, asset_b_df):
        """
        Calculates the Beta-Neutral spread and its Z-Score.
        Spread = log(AssetA) - (Beta * log(AssetB))
        """
        if asset_a_df is None or asset_b_df is None: return None
        
        # 1. Align Data
        combined = pd.concat([asset_a_df['Close'], asset_b_df['Close']], axis=1).dropna()
        combined.columns = ['A', 'B']
        
        if len(combined) < self.lookback: return None
        
        # 2. Log Prices (for relative change)
        log_a = np.log(combined['A'])
        log_b = np.log(combined['B'])
        
        # 3. Calculate Dynamic Beta
        rets_a = combined['A'].pct_change().dropna()
        rets_b = combined['B'].pct_change().dropna()
        beta = calculate_beta(rets_a, rets_b, window=self.lookback)
        
        # 4. Calculate Spread
        spread = log_a - (beta * log_b)
        
        # 5. Calculate Z-Score
        zscore = calculate_zscore(spread, window=self.lookback).iloc[-1]
        
        return {
            "zscore": round(zscore, 3),
            "beta": round(beta, 3),
            "spread_val": round(spread.iloc[-1], 5),
            "current_a": combined['A'].iloc[-1],
            "current_b": combined['B'].iloc[-1]
        }

    def find_best_index_basis_pair(self, tickers):
        """
        PRIORITY 1: Index-Basis Arbitrage.
        Trades an Asset against its Sector ETF (The 'Truth' level).
        Example: NVDA vs SOXX, AAPL vs QQQ.
        Includes BIST ADRs vs Emerging Markets.
        """
        BASIS_MAP = {
            "GOLD": "GDX",  # Barrick vs Gold Miners ETF
            "AEM": "GDX",   # Agnico Eagle vs Gold Miners ETF
            "BHP": "PICK",  # BHP vs Metals/Mining ETF
            "RIO": "PICK",  # Rio Tinto vs Metals/Mining ETF
            "VALE": "PICK", # Vale vs Metals/Mining ETF
            "FCX": "PICK",  # Freeport-McMoRan vs Metals/Mining ETF
            "PBR": "EWZ"    # Petrobras vs Brazil (High-Conviction Niche)
        }
        
        best_basis = None
        max_z = 0
        
        for asset, etf in BASIS_MAP.items():
            if asset not in tickers: continue
            
            try:
                df_a = get_live_market_data(asset, period="60d")
                df_b = get_live_market_data(etf, period="60d")
            except Exception as e:
                logger.warning(f"SCANNER: Skipping {asset}/{etf} basis due to data error: {e}")
                continue
            
            if df_a is None or df_b is None: continue
            
            rets_a = df_a['Close'].pct_change().dropna()
            rets_b = df_b['Close'].pct_change().dropna()
            corr = rets_a.corr(rets_b)
            
            if corr < 0.90: continue
            
            result = self.get_spread_zscore(df_a, df_b)
            if result and abs(result['zscore']) > abs(max_z):
                max_z = result['zscore']
                best_basis = {
                    "asset_a": asset,
                    "asset_b": etf,
                    "type": "INDEX_BASIS",
                    "correlation": corr,
                    **result
                }
        return best_basis

    def find_best_pair(self, tickers):
        """Hybrid Scanner."""
        basis_pair = self.find_best_index_basis_pair(tickers)
        if basis_pair and abs(basis_pair['zscore']) > self.z_threshold:
            return basis_pair
        return self._find_best_standard_pair(tickers)

    def _find_best_standard_pair(self, tickers):
        """Standard pair scanner logic."""
        best_pair = None
        max_divergence = 0
        data_map = {}
        for t in tickers:
            try:
                df = get_live_market_data(t, period="60d")
                if df is not None and not df.empty: data_map[t] = df
            except:
                logger.warning(f"SCANNER: Could not fetch {t}. Skipping.")
        
        active_tickers = list(data_map.keys())
        for i in range(len(active_tickers)):
            for j in range(i + 1, len(active_tickers)):
                t_a, t_b = active_tickers[i], active_tickers[j]
                rets_a = data_map[t_a]['Close'].pct_change().dropna()
                rets_b = data_map[t_b]['Close'].pct_change().dropna()
                corr = rets_a.corr(rets_b)
                if corr < 0.85: continue
                
                result = self.get_spread_zscore(data_map[t_a], data_map[t_b])
                if result and abs(result['zscore']) > abs(max_divergence):
                    max_divergence = result['zscore']
                    best_pair = {"asset_a": t_a, "asset_b": t_b, "type": "STANDARD", "correlation": corr, **result}
        return best_pair
