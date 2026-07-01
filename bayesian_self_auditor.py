import logging
from atomic_ops import atomic_read_json
from config_loader import config

logger = logging.getLogger("bayesian_audit")

class BayesianSelfAuditor:
    """
    Calibrates AI Confidence (Subjective) to Realized Win Rates (Empirical).
    Ensures the Kelly formula uses reality, not model optimism.
    """
    def __init__(self, journal_path="trade_journal.json"):
        self.journal_path = journal_path
        self.base_win_rates = {1: 0.35, 2: 0.45, 3: 0.50, 4: 0.58, 5: 0.65}

    def get_realized_edge(self):
        """Calculates win rates per confidence level from the last 100 trades."""
        trades = atomic_read_json(self.journal_path, [])
        if not trades: return self.base_win_rates
        
        # We only care about closed trades with an outcome
        history = [t for t in trades if "outcome" in t and "confidence_level" in t]
        if len(history) < 10: return self.base_win_rates # Not enough data
        
        realized_rates = {}
        for level in range(1, 6):
            level_trades = [t for t in history if t["confidence_level"] == level]
            if len(level_trades) < 5:
                # Use a blended approach if low sample size for a specific level
                realized_rates[level] = self.base_win_rates[level]
                continue
                
            wins = sum(1 for t in level_trades if t["outcome"] == "W")
            rate = wins / len(level_trades)
            
            # BLENDING: 50% Realized, 50% Base (Bayesian prior)
            # This prevents knee-jerk reactions to small sample sizes
            weight = min(1.0, len(level_trades) / 50) # Full weight at 50 trades
            blended = (rate * weight) + (self.base_win_rates[level] * (1 - weight))
            
            realized_rates[level] = round(blended, 3)
            logger.info(f"BAYESIAN UPDATE: Confidence Level {level} calibrated to {blended:.1%}")
            
        return realized_rates

if __name__ == "__main__":
    auditor = BayesianSelfAuditor()
    print(auditor.get_realized_edge())
