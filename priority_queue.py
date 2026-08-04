import os
import heapq
import time
import logging
from utils import setup_logging
from config_loader import config

logger = setup_logging("alpha_queue")

class AlphaQueue:
    """Priority-based opportunity queue."""
    def __init__(self, max_size=10):
        self.queue = [] # Min-heap (we use negative scores for max-priority)
        self.max_size = max_size

    def push(self, ticker, score, strategy_id="STAT_ARB", context=None):
        """
        Push a candidate trade into the queue.
        strategy_id: [STAT_ARB, TREND_FOLLOW, CONTRARIAN_TRAP]
        """
        strategy_weight = 2.0 if strategy_id == "CONTRARIAN_TRAP" else 1.0
        weighted_score = score * strategy_weight
        
        entry = (-weighted_score, time.time(), ticker, strategy_id, context)
        
        if len(self.queue) < self.max_size:
            heapq.heappush(self.queue, entry)
            logger.info(f"ALPHA_QUEUE: Pushed {ticker} ({strategy_id}) with weighted score {weighted_score:.2f}")
        else:
            if weighted_score > -self.queue[0][0]:
                heapq.heapreplace(self.queue, entry)
                logger.info(f"ALPHA_QUEUE: Replaced with high-tier {strategy_id} setup ({ticker})")

    def pop_best(self):
        """Returns the highest priority candidate."""
        if not self.queue:
            return None
        neg_score, timestamp, ticker, strat_id, context = heapq.heappop(self.queue)
        return {
            "ticker": ticker, 
            "strategy_id": strat_id,
            "score": -neg_score, 
            "context": context
        }

    def clear(self):
        self.queue = []

    def get_all_candidates(self):
        """Returns all candidates in the queue without removing them, sorted by priority."""
        sorted_items = sorted(self.queue, key=lambda x: x[0])
        return [
            {
                "ticker": item[2], 
                "strategy_id": item[3],
                "score": -item[0], 
                "context": item[4]
            }
            for item in sorted_items
        ]

def calculate_alpha_score(df, dist_to_h, dist_to_l):
    """
    Ranks a PoI hit.
    Now includes EXECUTION QUALITY (Spread-to-ATR ratio).
    """
    try:
        latest = df.iloc[-1]
        atr = latest['ATR_14']
        adx = latest['ADX_14']
        price = latest['Close']
        
        # 1. Proximity Weight
        min_dist = min(dist_to_h, dist_to_l)
        max_prox_score = config.get("trading.alpha_max_prox_score", 50.0)
        prox_score = max(0, max_prox_score * (1 - (min_dist / atr))) if atr > 0 else 0
        
        # 2. Execution Quality
        # Typical spread cost in dollars
        est_spread = price * (config.get("trading.fixed_spread_bps", 2.0) / 10000)
        spread_to_atr = est_spread / atr if atr > 0 else 1.0
        
        # Bonus for tight spreads
        max_exec_bonus = config.get("trading.alpha_max_exec_bonus", 50.0)
        spread_threshold = config.get("trading.alpha_spread_threshold", 0.12)
        exec_bonus = max(0, max_exec_bonus * (1 - (spread_to_atr / spread_threshold))) if spread_threshold > 0 else 0
        
        # 3. Regime Quality
        max_regime_score = config.get("trading.alpha_max_regime_score", 20.0)
        regime_score = min(max_regime_score, adx)
        
        total_score = prox_score + exec_bonus + regime_score
        return total_score
    except:
        return 0

if __name__ == "__main__":
    q = AlphaQueue()
    q.push("EURUSD", 45.5)
    q.push("BTCUSD", 89.2)
    q.push("AAPL", 12.1)
    
    best = q.pop_best()
    print(f"Processing Best Setup: {best['ticker']} (Score: {best['score']})")
