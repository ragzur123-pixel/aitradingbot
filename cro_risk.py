import os
import json
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from utils import setup_logging
from atomic_ops import atomic_read_json, atomic_write_json

# Alpaca SDK imports
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, OrderStatus

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging("alpaca_execution")

JOURNAL_PATH = "trade_journal.json"

class AlpacaExecutor:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        if not self.api_key or not self.secret_key:
            logger.error("ALPACA credentials missing in .env")
            self.client = None
        else:
            self.client = TradingClient(self.api_key, self.secret_key, paper=True)

    def get_account_buying_power(self):
        """Fetch current non-marginable buying power."""
        if not self.client: return 0
        try:
            account = self.client.get_account()
            return float(account.non_marginable_buying_power)
        except Exception as e:
            logger.error(f"Failed to fetch buying power: {e}")
            return 0

    def verify_order_fill(self, order_id, timeout=60):
        """
        Polling loop to verify if an order is FILLED.
        Prevents 'Execution Blindness' where we assume a submmited order is active.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                order = self.client.get_order_by_id(order_id)
                if order.status == OrderStatus.FILLED:
                    logger.info(f"ORDER FILLED: {order_id} at {order.filled_avg_price}")
                    return order
                elif order.status in [OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED]:
                    logger.error(f"ORDER FAILED: {order_id} status is {order.status}")
                    return None
                time.sleep(5) # Poll every 5 seconds
            except Exception as e:
                logger.error(f"Error checking order {order_id}: {e}")
                time.sleep(5)
        
        logger.warning(f"ORDER TIMEOUT: {order_id} not filled within {timeout}s.")
        return None

    def execute_bracket_limit_order(self, symbol, side, qty, entry_limit, stop_loss_price, take_profit_price):
        """Execute a Limit Bracket Order with Fill Verification."""
        if not self.client: return None

        # Buying Power Audit
        bp = self.get_account_buying_power()
        est_cost = qty * entry_limit
        if est_cost > bp:
            logger.error(f"INSUFFICIENT FUNDS: Est cost ${est_cost:.2f} > Buying Power ${bp:.2f}")
            return None

        order_side = OrderSide.BUY if side.upper() == "LONG" else OrderSide.SELL

        order_request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            limit_price=round(entry_limit, 5),
            time_in_force=TimeInForce.GTC,
            order_class=OrderClass.BRACKET,
            take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 5)),
            stop_loss=StopLossRequest(stop_price=round(stop_loss_price, 5))
        )

        try:
            order = self.client.submit_order(order_data=order_request)
            logger.info(f"ALPACA Order Submitted: {symbol} {side} ID: {order.id}")
            
            # VERIFICATION LOOP
            filled_order = self.verify_order_fill(order.id)
            if filled_order:
                return {
                    "order_id": str(filled_order.id),
                    "entry_price": float(filled_order.filled_avg_price), 
                    "status": "FILLED",
                    "qty": float(filled_order.filled_qty)
                }
            return None
        except Exception as e:
            logger.error(f"ALPACA Order Submission Failed: {e}")
            return None

    def get_total_equity(self):
        """Fetch real-time total portfolio equity (Balance + Open P/L)."""
        if not self.client: return 0
        try:
            account = self.client.get_account()
            return float(account.equity)
        except Exception as e:
            logger.error(f"Failed to fetch equity: {e}")
            return 0

    def execute_passive_maker_entry(self, symbol, side, qty, current_price):
        """
        Execute a Passive Maker Limit Order (Liquidity Provision).
        Turns the PFOF spread tax into a profit by waiting for the market to come to us.
        """
        if not self.client: return None

        # MAKER BUFFER: Negative bps places the limit INSIDE the spread
        maker_buffer_bps = config.get("trading.maker_limit_buffer_bps", -2.0)
        buffer_val = current_price * (abs(maker_buffer_bps) / 10000)
        
        # LONG: Buy slightly below current price. SHORT: Sell slightly above.
        limit_price = current_price - buffer_val if side == "LONG" else current_price + buffer_val

        order_side = OrderSide.BUY if side.upper() == "LONG" else OrderSide.SELL

        order_request = LimitOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            limit_price=round(limit_price, 5),
            time_in_force=TimeInForce.GTC # Needs time to sit on the book
        )

        try:
            logger.info(f"Submitting Passive Maker Limit ({side}): {symbol} at ${limit_price:.5f}")
            order = self.client.submit_order(order_data=order_request)
            
            # VERIFICATION LOOP (Wait up to 60s for the fill, otherwise cancel)
            filled_order = self.verify_order_fill(order.id, timeout=60)
            if filled_order:
                return {
                    "order_id": str(filled_order.id),
                    "entry_price": float(filled_order.filled_avg_price), 
                    "status": "FILLED",
                    "qty": float(filled_order.filled_qty)
                }
            else:
                logger.warning("Maker Limit not filled. Canceling order to avoid stale fills.")
                self.client.cancel_order_by_id(order.id)
                return None
        except Exception as e:
            logger.error(f"Maker Limit Failed: {e}")
            return None

class AsymmetricEntryOptimizer:
    """
    Prevents Hour-Boundary Manipulation with VWAP-Anchored Entry.
    Waits for price to revert to the 1-minute VWAP before firing.
    """
    @staticmethod
    def calculate_vwap(df):
        """Calculates 1-minute Volume Weighted Average Price."""
        v = df['Volume']
        p = (df['High'] + df['Low'] + df['Close']) / 3
        return (p * v).cumsum() / v.cumsum()

    @staticmethod
    async def get_optimal_fill_price(ticker, direction, target_price, timeout_minutes=15):
        """
        Monitors 1-minute candles.
        - Anchor: Buy if price touches the 1m VWAP (The 'Truth' level).
        - Chase: Buy if price moves > 0.6% (Avoid missing absolute breakouts).
        """
        from market_feed import get_live_market_data
        
        logger.info(f"VWAP-ANCHORED ENTRY ACTIVE: Seeking optimal fill for {ticker}")
        start_time = time.time()
        chase_threshold = 0.006 
        
        while (time.time() - start_time) < (timeout_minutes * 60):
            df = get_live_market_data(ticker, period="1m")
            if df is None or df.empty or len(df) < 5: 
                await asyncio.sleep(30)
                continue
                
            current = df['Close'].iloc[-1]
            vwap = AsymmetricEntryOptimizer.calculate_vwap(df).iloc[-1]
            price_change = (current / target_price) - 1
            
            # 1. VWAP ANCHOR GATE (The Institutional Fill)
            if direction == "LONG":
                # We wait for price to dip to or below VWAP
                if current <= vwap:
                    logger.info(f"VWAP ANCHOR HIT (LONG): Entry at ${current:.5f} (VWAP: ${vwap:.5f})")
                    return current
                
                # 2. EMERGENCY MOMENTUM CHASE
                if price_change > chase_threshold:
                    logger.warning(f"MOMENTUM ESCAPE: {ticker} mooning without VWAP touch. Entering.")
                    return current
                    
            else: # SHORT
                if current >= vwap:
                    logger.info(f"VWAP ANCHOR HIT (SHORT): Entry at ${current:.5f} (VWAP: ${vwap:.5f})")
                    return current
                
                if price_change < -chase_threshold:
                    logger.warning(f"MOMENTUM ESCAPE: {ticker} dumping without VWAP touch. Entering.")
                    return current
            
            await asyncio.sleep(20) 
            
        logger.warning(f"VWAP Anchor Timeout for {ticker}. Filling at Market.")
        df_final = get_live_market_data(ticker, period="1m")
        return df_final['Close'].iloc[-1] if df_final is not None else target_price

class AggressiveLimitEntry:
    """
    Targets a 1-minute wick touch (Discount) within an hourly breakout.
    Uses 'Tactical Limit' placement 0.2% below/above current price to catch spikes.
    """
    @staticmethod
    async def get_tactical_limit_fill(ticker, direction, target_price, timeout_minutes=10):
        """
        Places a Limit order slightly away from market and waits for a micro-dip.
        """
        from market_feed import get_live_market_data
        
        # Tactical Offset: 0.2%
        offset = 0.002
        limit_price = target_price * (1 - offset) if direction == "LONG" else target_price * (1 + offset)
        
        logger.info(f"TACTICAL LIMIT ACTIVE: Asset {ticker} | Limit: ${limit_price:.5f}")
        start_time = time.time()
        
        while (time.time() - start_time) < (timeout_minutes * 60):
            df = get_live_market_data(ticker, period="1m")
            if df is None or df.empty:
                await asyncio.sleep(20)
                continue
            
            low = df['Low'].iloc[-1]
            high = df['High'].iloc[-1]
            
            # Check if our limit would have been 'touched'
            if direction == "LONG" and low <= limit_price:
                logger.info(f"TACTICAL FILL (LONG): Price spiked to ${low:.5f}. Filled at ${limit_price:.5f}")
                return limit_price
            elif direction == "SHORT" and high >= limit_price:
                logger.info(f"TACTICAL FILL (SHORT): Price spiked to ${high:.5f}. Filled at ${limit_price:.5f}")
                return limit_price
                
            await asyncio.sleep(15)
            
        logger.warning(f"Tactical Limit Timeout. Filling at Mid-Price for {ticker}.")
        return target_price

async def finalize_trade_execution(ticker, direction, risk_val, confidence_level=3, manual_sl=None, manual_tp=None):
    """Hardened Small-Account Bridge with Passive Maker Limits and Asymmetric Entry."""
    executor = AlpacaExecutor()
    
    try:
        # Load snapshot...
        if not os.path.exists("market_snapshot.md"):
             logger.error("Snapshot missing. Cannot execute.")
             return
             
        with open("market_snapshot.md", "r") as f:
            content = f.read()
            match = re.search(r'Last Close Price\*\*: ([\d\.]+)', content)
            target_price = float(match.group(1)) if match else 0.0

        if target_price <= 0: return

        # --- PHASE 31: ASYMMETRIC ENTRY OPTIMIZATION ---
        # Instead of entering at the hour mark, we seek a better fill.
        entry_price = await AsymmetricEntryOptimizer.get_optimal_fill_price(ticker, direction, target_price)

        # 0. ACCOUNT RECONCILIATION
        equity = executor.get_total_equity()
        if equity <= 0: return

        # 1. SL / TP Calculation
        if manual_sl and manual_tp:
            # We must adjust SL/TP if the entry_price changed significantly
            # but for now we keep the deterministic anchors.
            stop_loss = manual_sl
            take_profit = manual_tp
        else:
            sl_pct = 0.015
            stop_loss = entry_price * (1 - sl_pct) if direction == "LONG" else entry_price * (1 + sl_pct)
            take_profit = entry_price * (1 + sl_pct * 3) if direction == "LONG" else entry_price * (1 - sl_pct * 3)

        # 2. QTY Calculation
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0: return
        qty = int(risk_val / risk_per_share)
        
        if qty <= 0:
            logger.warning(f"Sizing Veto: QTY is 0. Risk Val ${risk_val} too small.")
            return

        # --- PASSIVE MAKER ENTRY ---
        logger.info(f">>> EXECUTING PASSIVE MAKER: {direction} {ticker} | QTY: {qty} | Entry: {entry_price}")
        
        result = executor.execute_passive_maker_entry(ticker, direction, qty, entry_price)
        
        if result:
            update_journal_with_execution(ticker, direction, result, stop_loss, take_profit)
            
    except Exception as e:
        logger.error(f"Finalize Execution Error: {e}")

def update_journal_with_execution(ticker, direction, alpaca_data, sl, tp):
    """Update the trade journal with verified Alpaca data."""
    try:
        data = atomic_read_json(JOURNAL_PATH, [])
        for entry in reversed(data):
            if entry.get("asset") == ticker and entry.get("direction") == direction and entry.get("status") == "OPEN":
                entry.update(alpaca_data)
                entry["stop_loss"] = sl
                entry["take_profit"] = tp
                break
        atomic_write_json(JOURNAL_PATH, data)
        logger.info("Trade Journal updated with FILLED order data.")
    except Exception as e:
        logger.error(f"Journal Update Error: {e}")
