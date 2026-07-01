import os
import sqlite3
import logging
from utils import setup_logging
from database_manager import TradingDatabase

logger = setup_logging("strategy_auditor")

class StrategyAuditor:
    """
    Self-correcting meta-learning engine.
    Analyzes recent trade failures to update the AI's strategic bias.
    """
    def __init__(self, db_path="trading_state.db"):
        self.db = TradingDatabase(db_path)

    def generate_systemic_bias_report(self):
        """
        Analyzes the last 10 completed trades.
        Identifies if we are failing due to 'Stop Hunts', 'Chop', or 'Counter-Trend'.
        """
        try:
            # Query last 10 trades with an outcome
            with sqlite3.connect(self.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades WHERE outcome IS NOT NULL ORDER BY id DESC LIMIT 10")
                history = [dict(row) for row in cursor.fetchall()]

            if not history: return "No recent trade history for meta-learning."

            losses = [t for t in history if "L" in str(t['outcome']).upper()]
            wins = [t for t in history if "W" in str(t['outcome']).upper()]
            
            report = "### SYSTEMIC PERFORMANCE AUDIT (Meta-Learning):\n"
            report += f"- Win Rate (Last 10): {len(wins)*10}%\n"
            
            if len(losses) >= 5:
                report += "- 🚨 CRITICAL BIAS DETECTED: Recent high failure rate.\n"
                
                # Analyze common exit reasons
                reasons = [t.get("exit_reason", "UNKNOWN") for t in losses]
                if reasons.count("STOP_LOSS") > 3:
                    report += "- FAILURE PATTERN: Frequent Stop-Loss hits. ADVICE: Tighten 'Noise Floor' or avoid trading in low-ADX regimes.\n"
                if reasons.count("TRAILING_STOP") > 3:
                    report += "- FAILURE PATTERN: Trailing stops giving back too much profit. ADVICE: Increase TP aggression.\n"

            # Check for 'Revenge Trading' indicators
            assets = [t['asset'] for t in history]
            if len(set(assets)) < 3 and len(history) >= 5:
                report += "- WARNING: Over-concentration on few assets detected. Maintain diversification.\n"

            return report

        except Exception as e:
            logger.error(f"Strategy audit failed: {e}")
            return "Strategy auditor offline."

if __name__ == "__main__":
    auditor = StrategyAuditor()
    print(auditor.generate_systemic_bias_report())
