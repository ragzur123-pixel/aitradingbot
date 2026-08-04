import pandas as pd
import numpy as np
import logging
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from indicators import calculate_ou_params
from market_feed import get_live_market_data
from utils import setup_logging
from config_loader import config

logger = setup_logging("arbitrage_engine")

class CointegrationArbitrageEngine:
    """Statistical Arbitrage Engine (Cointegration-based)."""
    def __init__(self):
        self.lookback = 90
        self.z_threshold = config.get("trading.min_zscore_anomaly", 3.0)
        self.coint_pvalue_threshold = 0.05
        self.max_half_life = 30.0

    def get_cointegration_spread(self, asset_a_df, asset_b_df):
        """
        Calculates the spread using OLS regression and tests for Cointegration.
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
        
        # 3. Engle-Granger Cointegration Test
        # Test if A is cointegrated with B
        try:
            score, pvalue, _ = coint(log_a, log_b)
        except Exception as e:
            logger.debug(f"Cointegration test failed: {e}")
            return None
        
        if pvalue > self.coint_pvalue_threshold:
            return None # Not cointegrated
            
        # 4. Calculate Dynamic Hedge Ratio (Beta) using OLS
        # log_a = alpha + beta * log_b
        try:
            X = sm.add_constant(log_b)
            model = sm.OLS(log_a, X).fit()
            beta = model.params['B']
        except Exception as e:
            logger.debug(f"OLS Regression failed: {e}")
            return None
        
        # 5. Calculate Spread
        spread = log_a - (beta * log_b)
        
        # 6. Validate Mean-Reversion (Ornstein-Uhlenbeck)
        ou_params = calculate_ou_params(pd.Series(spread))
        if ou_params['half_life'] > self.max_half_life or ou_params['half_life'] <= 0:
            return None # Spread takes too long to revert
            
        # 7. Calculate Z-Score of Spread
        zscore = (spread.iloc[-1] - spread.mean()) / spread.std()
        
        return {
            "zscore": round(zscore, 3),
            "beta": round(beta, 3),
            "spread_val": round(spread.iloc[-1], 5),
            "p_value": round(pvalue, 4),
            "half_life": round(ou_params['half_life'], 2),
            "current_a": combined['A'].iloc[-1],
            "current_b": combined['B'].iloc[-1]
        }

    def find_best_index_basis_pair(self, tickers):
        """Index-Basis Arbitrage (Asset vs Sector ETF)."""
        BASIS_MAP = {
            "GOLD": "GDX",  
            "AEM": "GDX",   
            "BHP": "PICK",  
            "RIO": "PICK",  
            "VALE": "PICK", 
            "FCX": "PICK",  
            "PBR": "EWZ"    
        }
        
        best_basis = None
        max_z = 0
        
        for asset, etf in BASIS_MAP.items():
            if asset not in tickers: continue
            
            try:
                df_a = get_live_market_data(asset, period="180d") # Longer period for cointegration
                df_b = get_live_market_data(etf, period="180d")
            except Exception as e:
                logger.warning(f"SCANNER: Skipping {asset}/{etf} basis due to data error: {e}")
                continue
            
            result = self.get_cointegration_spread(df_a, df_b)
            if result and abs(result['zscore']) > abs(max_z):
                max_z = result['zscore']
                best_basis = {
                    "asset_a": asset,
                    "asset_b": etf,
                    "type": "INDEX_BASIS_COINT",
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
                df = get_live_market_data(t, period="180d")
                if df is not None and not df.empty: data_map[t] = df
            except:
                logger.warning(f"SCANNER: Could not fetch {t}. Skipping.")
        
        active_tickers = list(data_map.keys())
        for i in range(len(active_tickers)):
            for j in range(i + 1, len(active_tickers)):
                t_a, t_b = active_tickers[i], active_tickers[j]
                
                result = self.get_cointegration_spread(data_map[t_a], data_map[t_b])
                if result and abs(result['zscore']) > abs(max_divergence):
                    max_divergence = result['zscore']
                    best_pair = {"asset_a": t_a, "asset_b": t_b, "type": "STANDARD_COINT", **result}
        return best_pair

# Alias to avoid breaking older scripts temporarily
CorrelationArbitrageEngine = CointegrationArbitrageEngine
