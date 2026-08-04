"""WebSocket-based opportunity feeder with stat-arb scanning."""
import os
import asyncio
import json
import logging
from datetime import datetime, timezone
from alpaca.data.live import StockDataStream
from utils import setup_logging
from autonomous_pipeline import run_operation
from market_snapshot import create_market_snapshot

from priority_queue import AlphaQueue, calculate_alpha_score
from market_feed import get_live_market_data

from pairs_trading_scanner import CointegrationArbitrageEngine
from contrarian_module import ContrarianTrapHunter

logger = setup_logging("market_watcher")

class MarketWatcher:
    """Monitors live data for stat-arb and contrarian opportunities."""
    def __init__(self, tickers=["AAPL", "EURUSD=X", "GBPUSD=X"]):
        self.tickers = tickers
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.stream = StockDataStream(self.api_key, self.secret_key)
        self.queue = AlphaQueue(max_size=20)
        self.pairs_scanner = CointegrationArbitrageEngine()
        self.best_pair = None
        self.last_prices = {}



    async def _handle_trade(self, data):
        """Callback for real-time price updates (Thin-Packet Protocol)."""
        symbol = data.symbol
        current_price = data.price
        self.last_prices[symbol] = current_price
        
        # 1. Fetch data...
        df = get_live_market_data(symbol)
        if df is None: return

        # 2. Check for Contrarian Traps
        hunter = ContrarianTrapHunter()
        traps = hunter.identify_trap_scenarios(df)
        for trap in traps:
            logger.info(f"TRAP DETECTED: {symbol} - {trap['type']}")
            self.queue.push(symbol, 95.0, strategy_id="CONTRARIAN_TRAP", context=trap)

        # 3. Standard PoI Check...
        await self._check_standard_poi(symbol, current_price, df)
        
        # 4. Statistical Arbitrage Check...
        await self._check_pairs_arbitrage()

    async def _check_standard_poi(self, symbol, price, df):
        try:
            if df is None: return
            from geometry import calculate_swing_points
            df_swings = calculate_swing_points(df)
            last_high = df_swings['swing_high'].dropna().iloc[-1]
            last_low = df_swings['swing_low'].dropna().iloc[-1]

            score = calculate_alpha_score(df, abs(price - last_high), abs(price - last_low))
            if score > 45:
                self.queue.push(symbol, score, context={"type": "POI_HIT", "price": price})
        except Exception as e: logger.warning(f"PoI check error: {e}")

    async def _check_pairs_arbitrage(self):
        """Monitors Z-Score divergence of best cointegrated pair."""
        if not self.best_pair: return
        p1 = self.best_pair['asset_a']
        p2 = self.best_pair['asset_b']
        
        if p1 in self.last_prices and p2 in self.last_prices:
            # Fetch history for Z-Score
            df1 = get_live_market_data(p1, period="180d")
            df2 = get_live_market_data(p2, period="180d")

            result = self.pairs_scanner.get_cointegration_spread(df1, df2)
            if result:
                z = result['zscore']
                if abs(z) > 2.0: # 2 Standard Deviations
                    score = 80.0 # High Alpha
                    side = "LONG_SPREAD" if z < -2.0 else "SHORT_SPREAD"
                    logger.info(f"STAT-ARB TRIGGER: {p1}/{p2} spread Z-Score is {z:.2f} ({side})")
                    self.queue.push(f"{p1}_{p2}", score, strategy_id="STAT_ARB", context={"type": "PAIRS_ARB", "zscore": z})

    async def start(self):
        # Initial Cointegration Scan
        self.best_pair = self.pairs_scanner.find_best_pair(self.tickers)

        if self.best_pair:
            logger.info(f"Subscribing to feeds. Monitoring {self.best_pair['asset_a']} and {self.best_pair['asset_b']}.")
        else:
            logger.info("No viable pairs found.")
        for ticker in self.tickers:
            symbol, _ = get_alpaca_symbol(ticker)
            self.stream.subscribe_trades(self._handle_trade, symbol)

        await self.stream._run_forever()


if __name__ == "__main__":
    watcher = MarketWatcher(["AAPL"])
    asyncio.run(watcher.start())
