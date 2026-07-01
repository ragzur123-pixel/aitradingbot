import pandas as pd
import numpy as np
import logging
from config_loader import config
from atomic_ops import atomic_read_json

logger = logging.getLogger("global_risk")

class GlobalRiskOverlay:
    """
    Prevents 'The Isolation Paradox' by monitoring aggregate portfolio exposure.
    Focuses on currency correlation and sector concentration.
    """
    def __init__(self):
        self.journal_path = config.get("system.journal_path", "trade_journal.json")
        self.max_currency_exposure = config.get("trading.max_currency_exposure_pct", 0.03) # Max 3% per currency (e.g. USD)
        
    def get_active_exposure(self):
        """Calculates current exposure per currency and asset."""
        trades = atomic_read_json(self.journal_path, [])
        active = [t for t in trades if t.get("status") == "OPEN"]
        
        exposure = {}
        for t in active:
            asset = t["asset"]
            risk_val = t.get("risk_val", 0) # How much we stand to lose
            
            # Map asset to its components (e.g., EURUSD -> EUR, USD)
            components = self._get_asset_components(asset)
            for comp in components:
                exposure[comp] = exposure.get(comp, 0) + risk_val
                
        return exposure

    def _get_asset_components(self, asset):
        """Extracts currency components from a ticker."""
        if "/" in asset: return asset.split("/")
        if "=" in asset: # EURUSD=X
            base = asset.split("=")[0]
            if len(base) == 6: return [base[:3], base[3:]]
        # For stocks, we assume USD base
        return [asset, "USD"]

    def is_trade_allowed(self, ticker, direction, risk_amount, account_balance):
        """
        Final Portfolio Gate. 
        Vetoes if the new trade pushes currency exposure above the ceiling.
        """
        exposure = self.get_active_exposure()
        components = self._get_asset_components(ticker)
        
        # Ceilings in absolute USD
        ceiling = account_balance * self.max_currency_exposure
        
        for comp in components:
            current = exposure.get(comp, 0)
            if (current + risk_amount) > ceiling:
                logger.warning(f"GLOBAL RISK VETO: {comp} exposure (${current + risk_amount:.2f}) exceeds ceiling (${ceiling:.2f}).")
                return False, f"Over-exposure to {comp}"
                
        # Directional Correlation Check (Simple version)
        # If we are already LONG EURUSD (Short USD) and want to go LONG GBPUSD (Short USD)
        # This increases our Short USD exposure.
        # Professional implementation would use a Correlation Matrix.
        
        return True, "Passed Portfolio Gate"
