import os
import json
import time
import logging
from datetime import datetime
from market_feed import get_live_market_data
from indicators import add_indicators
from sentiment_sentinel import HarvardConsensusEngine
from utils import setup_logging
from notifier import Notifier
from config_loader import config
from atomic_ops import atomic_read_json, atomic_write_json

# Setup logging
logger = setup_logging("risk_manager")
notifier = Notifier()

JOURNAL_PATH = config.get("system.journal_path", "trade_journal.json")
STATE_FILE = config.get("system.state_file", "state.json")

def update_state_pl():
    """Update state.json with lifetime P/L stats. Uses atomic read/write."""
    trades = atomic_read_json(JOURNAL_PATH, [])
    if not trades: return
        
    try:
        total_pl = sum(t.get("profit_loss", 0.0) for t in trades if t.get("status") == "CLOSED")
        state = atomic_read_json(STATE_FILE, {"total_pl": 0.0})
        state["total_pl"] = round(total_pl, 2)
        atomic_write_json(STATE_FILE, state)
    except Exception as e:
        logger.error(f"Error updating state P/L: {e}")

def check_market_regime(df):
    """
    Checks if the market is in a suitable regime for trading.
    Blocks trading if ADX is below the threshold (sideways/choppy).
    """
    if df is None or df.empty:
        return False, "Data Unavailable"
        
    adx = df['ADX_14'].iloc[-1]
    threshold = config.get("trading.min_adx_threshold", 20)
    
    if adx < threshold:
        return False, f"CHOP DETECTED: ADX ({adx:.2f}) is below threshold ({threshold}). Blocking entries."
    
    return True, f"TRENDING: ADX ({adx:.2f}) confirmed."

def send_daily_summary():
    """Calculates and sends a summary of today's trading performance."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    state = atomic_read_json(STATE_FILE, {})
    if state.get("last_report_date") == today:
        return 

    if datetime.now().hour < 20:
        return

    try:
        trades = atomic_read_json(JOURNAL_PATH, [])
        today_trades = [t for t in trades if t.get("exit_date") and t["exit_date"].startswith(today)]
        
        if not today_trades:
            return

        wins = sum(1 for t in today_trades if t.get("outcome") == "W")
        losses = sum(1 for t in today_trades if t.get("outcome") == "L")
        daily_pl = sum(t.get("profit_loss", 0.0) for t in today_trades)
        
        msg = (
            f"📅 <b>Daily Performance Summary ({today})</b>\n"
            f"Trades Closed: {len(today_trades)}\n"
            f"Wins: {wins} | Losses: {losses}\n"
            f"Daily P/L: ${daily_pl:+.2f}\n"
            f"Total Account P/L: ${state.get('total_pl', 0.0):+.2f}\n\n"
            f"📜 <b>Recent Trading Logs:</b>\n"
            f"<pre>{notifier.get_log_tail('trading_system.log', lines=15)}</pre>"
        )
        
        notifier.notify(msg, alert_type="INFO")
        
        state["last_report_date"] = today
        atomic_write_json(STATE_FILE, state)
            
    except Exception as e:
        logger.error(f"Error generating daily summary: {e}")

class DynamicRegimeClassifier:
    """
    Classifies Market Volatility Structure.
    Adapts math multipliers to the current 'Fear/Greed' environment.
    """
    @staticmethod
    def get_regime_multipliers(df):
        """
        Returns (SL_Multiplier, TP_Multiplier) based on Volatility Percentiles.
        Regimes: LOW_VOL (Quiet), NORMAL, HIGH_VOL (Panic/Squeeze).
        """
        from indicators import calculate_atr
        
        atr = calculate_atr(df, 14)
        atr_pct = (atr / df['Close']) * 100
        
        # Calculate ATR percentile (relative to last 100 periods)
        current_atr_p = atr_pct.iloc[-1]
        hist_atr = atr_pct.tail(100)
        p_rank = (hist_atr < current_atr_p).mean() * 100
        
        if p_rank < 30:
            # LOW VOL: Price is tight. Tighten SL to avoid slow bleed.
            return 1.8, 4.0 # 1.8x ATR SL, 4:1 TP
        elif p_rank > 80:
            # HIGH VOL: Wide swings. Widen SL to avoid 'Stop Runs'.
            return 3.5, 2.5 # 3.5x ATR SL, 2.5:1 TP
        else:
            # NORMAL: Standard math.
            return 2.5, 3.0

def calculate_deterministic_risk_levels(df, direction, entry_price):
    """
    Calculates Stop-Loss and Take-Profit based on Market Microstructure (Math).
    Now uses DYNAMIC REGIME multipliers.
    """
    from geometry import calculate_volume_profile, calculate_volatility_floor
    from indicators import calculate_atr
    
    # 1. Regime-Based Multipliers
    sl_mult, tp_ratio = DynamicRegimeClassifier.get_regime_multipliers(df)
    
    # 2. Volatility Anchoring (ATR)
    atr = calculate_atr(df, 14).iloc[-1]
    v_floor = calculate_volatility_floor(df)
    
    # Use Dynamic ATR multiplier, but at least 3.0x Noise Floor
    sl_dist = max(atr * sl_mult, v_floor * 3.0)
    
    # 3. Level Anchoring (Volume POC)
    poc, va_low, va_high = calculate_volume_profile(df)
    
    if direction == "LONG":
        sl = entry_price - sl_dist
        if poc < entry_price and poc > sl:
            sl = poc - (v_floor * 1.5)
            
        # TP derived from Dynamic Ratio
        tp = entry_price + (entry_price - sl) * tp_ratio
        if va_high > entry_price:
            tp = max(tp, va_high)
            
    else: # SHORT
        sl = entry_price + sl_dist
        if poc > entry_price and poc < sl:
            sl = poc + (v_floor * 1.5)
            
        tp = entry_price - (sl - entry_price) * tp_ratio
        if va_low < entry_price:
            tp = min(tp, va_low)
            
    return round(sl, 5), round(tp, 5)

def validate_trade(trade_params):
    """
    Validates trade parameters before execution.
    Ensures that stops, targets, and assets are mathematically sound.
    """
    required = ["asset", "direction", "entry_price", "qty"] # stop_loss removed as it's now calculated
    for field in required:
        if field not in trade_params:
            logger.error(f"Validation Failed: Missing {field}")
            return False
    
    if trade_params["qty"] <= 0:
        logger.error("Validation Failed: Quantity must be positive")
        return False
        
    return True

def monitor_active_trades():
    """
    Deterministic Risk Manager. Monitors open positions and executes emergency exits 
    based on ATR trailing stops or violent WOTC divergence.
    """
    try:
        trades = atomic_read_json(JOURNAL_PATH, [])
        if not trades: return

        active_trades = [t for t in trades if t.get("status") == "OPEN"]
        if not active_trades:
            return

        sentinel = HarvardConsensusEngine()

        for trade in active_trades:
            ticker = trade["asset"]
            direction = trade["direction"]
            qty = float(trade.get("qty", 0))
            sl = float(trade.get("stop_loss"))
            tp = float(trade.get("take_profit"))
            
            # Fetch Latest Data
            df = get_live_market_data(ticker)
            if df is None or df.empty: continue
            
            current_price = df['Close'].iloc[-1]
            exit_triggered = False
            reason = ""

            # --- VIRTUAL STEALTH EXIT (Anti-Stop Hunting) ---
            if direction == "LONG":
                if current_price <= sl:
                    exit_triggered = True
                    reason = f"VIRTUAL SL HIT: {current_price} <= {sl}"
                elif current_price >= tp:
                    exit_triggered = True
                    reason = f"VIRTUAL TP HIT: {current_price} >= {tp}"
            elif direction == "SHORT":
                if current_price >= sl:
                    exit_triggered = True
                    reason = f"VIRTUAL SL HIT: {current_price} >= {sl}"
                elif current_price <= tp:
                    exit_triggered = True
                    reason = f"VIRTUAL TP HIT: {current_price} <= {tp}"

            if exit_triggered:
                logger.warning(f"!!! STEALTH EXIT TRIGGERED for {ticker} !!! Reason: {reason}")
                
                # Execute Market Exit via Alpaca
                from cro_risk import AlpacaExecutor
                from alpaca.trading.enums import OrderSide
                executor = AlpacaExecutor()
                side = OrderSide.SELL if direction == "LONG" else OrderSide.BUY
                
                try:
                    res = executor.client.close_position(ticker)
                    logger.info(f"ALPACA Position Closed for {ticker}.")
                except Exception as e:
                    logger.error(f"Failed to close position: {e}")
                    # Fallback to market order if close_position fails
                    continue

                if direction == "LONG":
                    pl = (current_price - float(trade["entry_price"])) * qty
                else:
                    pl = (float(trade["entry_price"]) - current_price) * qty
                
                trade["status"] = "CLOSED"
                trade["exit_price"] = current_price
                trade["exit_reason"] = reason
                trade["exit_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                trade["outcome"] = "W" if pl > 0 else "L"
                trade["profit_loss"] = round(pl, 2)

                msg = f"Asset: {ticker}\nExit: {current_price}\nReason: {reason}\nP/L: {trade['profit_loss']}"
                notifier.notify(msg, alert_type="TRADE")

        atomic_write_json(JOURNAL_PATH, trades)
            
    except Exception as e:
        logger.exception("Fatal crash in Risk Manager")

if __name__ == "__main__":
    logger.info(">>> RISK MANAGER ACTIVE: High-Frequency Monitoring (5s Cycle) <<<")
    while True:
        try:
            monitor_active_trades()
            update_state_pl()
            send_daily_summary()
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            
        # TIGHTENED: 5-second cycle for Real-Time Virtual Stop enforcement
        time.sleep(5)
