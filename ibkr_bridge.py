import logging
import os
from config_loader import config

# Using ib_insync for high-level IBKR API interaction
# Requires: pip install ib_insync
import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
try:
    from ib_insync import IB, Stock, LimitOrder, MarketOrder
except ImportError:
    logging.warning("IBKR: ib_insync not installed. Bridge in simulation mode.")

logger = logging.getLogger("ibkr_bridge")

class IBKRBridge:
    """IBKR Pro integration stub."""
    def __init__(self):
        self.ib = None
        self.connected = False
        self.port = config.get("trading.ibkr_port", 7497)
        self.client_id = config.get("trading.ibkr_client_id", 1)

    def connect(self):
        """Connect to TWS or IB Gateway."""
        try:
            self.ib = IB()
            self.ib.connect('127.0.0.1', self.port, clientId=self.client_id)
            self.connected = True
            logger.info(f"IBKR: Connected on port {self.port}")
        except Exception as e:
            logger.error(f"IBKR: Connection Failed: {e}")
            self.connected = False

    def get_market_price(self, symbol):
        """Fetches market price. Uses market_feed as a fallback if not connected."""
        if not self.connected:
            from market_feed import get_live_market_data
            logger.warning(f"IBKR: Simulation Mode - Fetching {symbol} via market_feed")
            df = get_live_market_data(symbol, period="1d", interval="1d")
            if df is not None and not df.empty:
                return float(df['Close'].iloc[-1])
            return None
        
        contract = Stock(symbol, 'SMART', 'USD')
        # True IBKR integration would request tick data here:
        # ticker = self.ib.reqMktData(contract, '', False, False)
        # self.ib.sleep(2)
        # return ticker.marketPrice()
        
        # In absence of full TWS API, fallback to market_feed
        from market_feed import get_live_market_data
        df = get_live_market_data(symbol, period="1d", interval="1d")
        if df is not None and not df.empty:
            return float(df['Close'].iloc[-1])
        return None

    def apply_randomized_offset(self, price, side):
        """Adds small random jitter to limit price."""
        import random
        jitter_pct = random.uniform(0.0001, 0.0005)
        offset = price * jitter_pct
        
        if side == "BUY":
            return price - offset # Be slightly less aggressive
        else:
            return price + offset

    def execute_dma_order(self, symbol, side, qty, limit_price=None):
        """Executes an order."""
        if not self.connected:
            logger.warning(f"IBKR: Simulation Mode - Executing {side} {symbol} (DMA)")
            return {"status": "SIMULATED", "order_id": "DMA_MOCK"}

        # Apply Randomized Jitter to avoid algo-sniffing
        if limit_price and config.get("trading.randomize_limit_offsets", True):
            original = limit_price
            limit_price = self.apply_randomized_offset(limit_price, side)
            logger.info(f"IBKR: Randomized Limit: {original:.5f} -> {limit_price:.5f}")

        contract = Stock(symbol, 'SMART', 'USD')
        order = LimitOrder(side, qty, limit_price) if limit_price else MarketOrder(side, qty)
        
        trade = self.ib.placeOrder(contract, order)
        return trade

    def disconnect(self):
        if self.ib:
            self.ib.disconnect()
            logger.info("IBKR: Disconnected.")

if __name__ == "__main__":
    bridge = IBKRBridge()
    # bridge.connect() # Test on Launch Day
