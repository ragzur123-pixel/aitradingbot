import os
import asyncio
import json
import logging
from datetime import datetime, timezone
from alpaca.data.live import StockDataStream
from utils import setup_logging
from autonomous_pipeline import run_operation
from market_snapshot import create_market_snapshot
from geometry import check_geometric_distance

from priority_queue import AlphaQueue, calculate_alpha_score
from market_feed import get_live_market_data

from pairs_trading_scanner import PairsScanner

logger = setup_logging("market_watcher")

class MarketWatcher:
    """
    WebSocket-based Opportunity Feeder.
    Now includes Statistical Arbitrage (Pairs) monitoring.
    """
    def __init__(self, tickers=["AAPL", "EURUSD=X", "GBPUSD=X"]):
        self.tickers = tickers
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.stream = StockDataStream(self.api_key, self.secret_key)
        self.queue = AlphaQueue(max_size=20)
        self.pairs_scanner = PairsScanner(tickers=self.tickers)
        self.cointegrated_pairs = []
        self.last_prices = {}

from contrarian_module import ContrarianTrapHunter

# ... (init setup)

    async def _handle_trade(self, data):
        """Callback for real-time price updates (Thin-Packet Protocol)."""
        symbol = data.symbol
        current_price = data.price
        self.last_prices[symbol] = current_price
        
        # 1. Fetch data...
        df = get_live_market_data(symbol)
        if df is None: return

        # 2. Check for Contrarian Traps (Phase 2026 Alpha)
        hunter = ContrarianTrapHunter()
        traps = hunter.identify_trap_scenarios(df)
        for trap in traps:
            logger.info(f"🎯 TRAP DETECTED: {symbol} - {trap['type']}")
            self.queue.push(symbol, 95.0, strategy_id="CONTRARIAN_TRAP", context=trap)

        # 3. Standard PoI Check...
        await self._check_standard_poi(symbol, current_price, df)
        
        # 4. Statistical Arbitrage Check...
        await self._check_pairs_arbitrage()

    async def _check_standard_poi(self, symbol, price, df):
        try:
            from geometry import calculate_swing_points
            df_swings = calculate_swing_points(df)
            # ... (rest of function)

    async def _check_standard_poi(self, symbol, price):
        try:
            df = get_live_market_data(symbol)
            if df is None: return

            from geometry import calculate_swing_points
            df_swings = calculate_swing_points(df)
            last_high = df_swings['swing_high'].dropna().iloc[-1]
            last_low = df_swings['swing_low'].dropna().iloc[-1]

            score = calculate_alpha_score(df, abs(price - last_high), abs(price - last_low))
            if score > 45:
                self.queue.push(symbol, score, context={"type": "POI_HIT", "price": price})
        except: pass

    async def _check_pairs_arbitrage(self):
        """Monitors Z-Score divergence of cointegrated pairs."""
        for p1, p2, pval in self.cointegrated_pairs:
            if p1 in self.last_prices and p2 in self.last_prices:
                s1_price = self.last_prices[p1]
                s2_price = self.last_prices[p2]

                # Fetch history for Z-Score
                df1 = get_live_market_data(p1, period="5d")
                df2 = get_live_market_data(p2, period="5d")

                if df1 is not None and df2 is not None:
                    z = self.pairs_scanner.calculate_zscore(df1['Close'], df2['Close'])

                    if abs(z) > 2.0: # 2 Standard Deviations
                        score = 80.0 # High Alpha
                        side = "LONG_SPREAD" if z < -2.0 else "SHORT_SPREAD"
                        logger.info(f"🚨 STAT-ARB TRIGGER: {p1}/{p2} spread Z-Score is {z:.2f} ({side})")
                        self.queue.push(f"{p1}_{p2}", score, context={"type": "PAIRS_ARB", "zscore": z})

    async def start(self):
        # Initial Cointegration Scan
        self.cointegrated_pairs = self.pairs_scanner.find_cointegrated_pairs()

        logger.info(f"Subscribing to feeds. Monitoring {len(self.cointegrated_pairs)} Pairs.")
        for ticker in self.tickers:
            symbol, _ = get_alpaca_symbol(ticker)
            self.stream.subscribe_trades(self._handle_trade, symbol)

        await self.stream._run_forever()


if __name__ == "__main__":
    watcher = MarketWatcher("AAPL")
    asyncio.run(watcher.start())
