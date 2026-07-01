import logging
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from database_manager import TradingDatabase
from offline_backtest import StrategySimulator
from strategy_library import STRATEGY_MAP
from market_feed import get_live_market_data
from config_loader import config

logger = logging.getLogger("evolution_engine")

class EvolutionEngine:
    """
    Self-Evolving Strategy Optimizer.
    Runs 'Walk-Forward' backtests on realized market data to shift fund weights.
    """
    def __init__(self):
        self.db = TradingDatabase()

    def run_weekly_evolution(self):
        """Analyzes the last 30 days and updates the capital allocator."""
        logger.info("Starting Weekly Strategy Evolution (30-Day Lookback)...")
        
        tickers = config.get("trading.portfolio_tickers", ["EURUSD=X"])
        performance = {}

        for strat_name, strategy in STRATEGY_MAP.items():
            logger.info(f"Evolving {strat_name}...")
            total_strat_pl = 0.0
            
            for ticker in tickers:
                # 1. Fetch Realized Market Data (Last 30 days, 60m interval)
                df = get_live_market_data(ticker, period="30d", interval="60m")
                if df is None or df.empty: continue
                
                # 2. Run Simulated Post-Mortem
                sim = StrategySimulator(initial_balance=1000)
                # This is a simplified walk-forward:
                # We check how the strategy WOULD have performed last week
                for i in range(50, len(df)):
                    window = df.iloc[:i]
                    signal = strategy.get_signal(window)
                    
                    if signal and not sim.active_trade:
                        sim.simulate_trade(
                            ticker, signal['direction'], 
                            df['Close'].iloc[i], 10, # $10 risk unit
                            df['ATR_14'].iloc[i], df.index[i]
                        )
                    
                    if sim.active_trade:
                        sim.update(df['Close'].iloc[i], df['ATR_14'].iloc[i], df.index[i])

                total_strat_pl += (sim.balance - 1000)

            performance[strat_name] = total_strat_pl

        # 3. Update Allocator Weights in DB
        self._update_allocator_weights(performance)
        logger.info(f"Evolution complete. Performance Matrix: {performance}")

    def _update_allocator_weights(self, performance):
        """Calculates new weights based on expectancy."""
        total_pl = sum(max(0, v) for v in performance.values())
        if total_pl <= 0:
            logger.warning("No strategy was profitable last week. Reverting to equal weights.")
            new_weights = {k: 0.33 for k in performance.keys()}
        else:
            new_weights = {k: max(0.1, v / total_pl) for k, v in performance.items()}

        # Save to SQLite system_state
        for strat, weight in new_weights.items():
            self.db.set_state(f"weight_{strat}", weight)
        
        logger.info(f"NEW FUND WEIGHTS: {new_weights}")

if __name__ == "__main__":
    engine = EvolutionEngine()
    engine.run_weekly_evolution()
