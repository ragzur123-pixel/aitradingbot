import os
import json
import logging
import time
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta, timezone
from market_feed import add_indicators, get_structured_context
from indicators import add_indicators
import importlib
trading_bot = importlib.import_module("5_trading_bot")
calculate_position_size = trading_bot.calculate_position_size
get_calibrated_probability = trading_bot.get_calibrated_probability

from config_loader import config

# Setup logging for simulator
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIMULATOR] %(message)s",
    handlers=[logging.FileHandler("backtest_results.log"), logging.StreamHandler()]
)
logger = logging.getLogger("simulator")

class StrategySimulator:
    def __init__(self, initial_balance=10000):
        self.balance = initial_balance
        self.equity_curve = [initial_balance]
        self.trades = []
        self.active_trade = None

    def simulate_trade(self, ticker, direction, entry_price, risk_val, atr, timestamp):
        """Simulates a trade with realistic SL/TP and friction."""
        if self.active_trade:
            return

        # Phase 18: Realistic Entry Slippage
        # We assume the bot is slow and gets a worse fill than the 'Last Close'
        slippage_bps = config.get("trading.fixed_spread_bps", 2.0) + config.get("trading.latency_tax_bps", 2.5)
        friction_factor = 1 + (slippage_bps / 10000)
        
        real_entry = entry_price * friction_factor if direction == "LONG" else entry_price / friction_factor

        sl_dist = atr * 1.5
        tp_dist = atr * 3.0
        
        stop_loss = real_entry - sl_dist if direction == "LONG" else real_entry + sl_dist
        take_profit = real_entry + tp_dist if direction == "LONG" else real_entry - tp_dist
        qty = risk_val / sl_dist

        self.active_trade = {
            "ticker": ticker,
            "direction": direction,
            "entry_price": real_entry,
            "qty": qty,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "high_water_mark": real_entry if direction == "LONG" else 999999,
            "low_water_mark": real_entry if direction == "SHORT" else 0,
            "entry_time": timestamp
        }
        logger.info(f"SIM ENTRY: {direction} {ticker} at {real_entry:.5f} | SL: {stop_loss:.5f}")

    def update(self, current_price, atr, timestamp):
        """Updates active trade and checks for exits."""
        if not self.active_trade:
            return

        trade = self.active_trade
        direction = trade["direction"]
        exit_triggered = False
        reason = ""
        
        trail_mult = config.get("trading.trailing_stop_atr_mult", 2.0)

        if direction == "LONG":
            trade["high_water_mark"] = max(trade["high_water_mark"], current_price)
            trailing_stop = trade["high_water_mark"] - (atr * trail_mult)
            
            if current_price <= trade["stop_loss"]:
                exit_triggered = True
                reason = "STOP_LOSS"
            elif current_price >= trade["take_profit"]:
                exit_triggered = True
                reason = "TAKE_PROFIT"
            elif current_price <= trailing_stop:
                exit_triggered = True
                reason = "TRAILING_STOP"
        
        else: # SHORT
            trade["low_water_mark"] = min(trade["low_water_mark"], current_price)
            trailing_stop = trade["low_water_mark"] + (atr * trail_mult)
            
            if current_price >= trade["stop_loss"]:
                exit_triggered = True
                reason = "STOP_LOSS"
            elif current_price <= trade["take_profit"]:
                exit_triggered = True
                reason = "TAKE_PROFIT"
            elif current_price >= trailing_stop:
                exit_triggered = True
                reason = "TRAILING_STOP"

        if exit_triggered:
            # Phase 18: Exit Slippage
            # Assume 0.05% slippage on exit
            slippage_pct = config.get("trading.slippage_buffer_pct", 0.0005)
            real_exit = current_price * (1 - slippage_pct) if direction == "LONG" else current_price * (1 + slippage_pct)
            
            pl = (real_exit - trade["entry_price"]) * trade["qty"] if direction == "LONG" else (trade["entry_price"] - real_exit) * trade["qty"]
            
            self.balance += pl
            self.equity_curve.append(self.balance)
            
            trade["exit_price"] = real_exit
            trade["exit_time"] = timestamp
            trade["pl"] = pl
            trade["reason"] = reason
            self.trades.append(trade)
            
            logger.info(f"SIM EXIT: {reason} at {real_exit:.5f} | P/L: ${pl:.2f} | Balance: ${self.balance:.2f}")
            self.active_trade = None

def run_backtest(ticker="AAPL", days=30):
    logger.info(f"--- STARTING BACKTEST: {ticker} ({days} days) ---")
    
    # 1. Fetch Historical Data
    df = yf.download(ticker, period=f"{days}d", interval="15m")
    if df.empty:
        logger.error("No data found for backtest.")
        return

    # Flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = add_indicators(df)
    sim = StrategySimulator()
    
    # 2. Sequential Simulation (The Crucible)
    # We step through time, bar by bar
    for i in range(50, len(df)):
        current_bar = df.iloc[i]
        timestamp = df.index[i]
        
        # Every 4 hours (simulated), we 'Wake the LLM'
        if i % 16 == 0: 
            logger.info(f"Processing Simulated Interval: {timestamp}")
            
            # --- MOCK LLM DECISION ---
            # In a real backtest, you would pass df.iloc[:i] to the bot.
            # Here we simulate the logic for speed.
            prob = 0.55 # Assume 55% win rate strategy
            payoff = 2.5 # Assume 2.5:1 RR
            
            # Use real position sizing logic
            risk_val, _, _ = calculate_position_size(prob, payoff, sim.balance, current_bar['Close'])
            
            if risk_val > 0 and not sim.active_trade:
                # Random direction for demo, in real it uses LLM thesis
                direction = "LONG" if current_bar['RSI_14'] < 40 else "SHORT" if current_bar['RSI_14'] > 60 else None
                if direction:
                    sim.simulate_trade(ticker, direction, current_bar['Close'], risk_val, current_bar['ATR_14'], timestamp)

        # Update Simulator
        sim.update(current_bar['Close'], current_bar['ATR_14'], timestamp)

    # 3. Final Report
    wins = [t for t in sim.trades if t['pl'] > 0]
    losses = [t for t in sim.trades if t['pl'] <= 0]
    win_rate = len(wins) / len(sim.trades) if sim.trades else 0
    total_pl = sim.balance - 10000
    
    print("\n" + "="*50)
    print(f" BACKTEST COMPLETE: {ticker}")
    print(f" Total Trades: {len(sim.trades)}")
    print(f" Win Rate: {win_rate:.1%}")
    print(f" Total P/L: ${total_pl:.2f}")
    print(f" Final Balance: ${sim.balance:.2f}")
    print("="*50)

if __name__ == "__main__":
    run_backtest("AAPL", days=14)
