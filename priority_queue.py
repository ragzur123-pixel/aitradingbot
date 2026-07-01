import os
import heapq
import time
import logging
from utils import setup_logging

logger = setup_logging("alpha_queue")

class AlphaQueue:
    """
    Priority-based opportunity queue. 
    Ranks ticker hits by 'Alpha Score' (Proximity + Regime Quality).
    Ensures the bot processes the 'God-Tier' setup first.
    """
    def __init__(self, max_size=10):
        self.queue = [] # Min-heap (we use negative scores for max-priority)
        self.max_size = max_size

    def push(self, ticker, score, strategy_id="STAT_ARB", context=None):
        """
        Push a candidate trade into the queue.
        strategy_id: [STAT_ARB, TREND_FOLLOW, CONTRARIAN_TRAP]
        """
        # Phase 18: Strategy Weighting
        # Contrarian traps are 'God-Tier' Alpha. We double their priority.
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
        prox_score = max(0, 50 * (1 - (min_dist / atr))) if atr > 0 else 0
        
        # 2. Execution Quality (Phase 11 Hardening)
        # Typical spread cost in dollars
        est_spread = price * (config.get("trading.fixed_spread_bps", 2.0) / 10000)
        spread_to_atr = est_spread / atr if atr > 0 else 1.0
        
        # Bonus for tight spreads: +50 if spread is < 5% of ATR
        exec_bonus = max(0, 50 * (1 - (spread_to_atr / 0.12))) 
        
        # 3. Regime Quality
        regime_score = min(20, adx)
        
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
