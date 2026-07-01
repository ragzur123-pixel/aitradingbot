import sqlite3
import logging
import json
from datetime import datetime, timezone, timedelta
from config_loader import config

logger = logging.getLogger("research_historian")

class ResearchHistorian:
    """
    Logs AI Reasoning vs. Market Reality.
    Builds the 'Institutional Edge' through long-term data collection.
    """
    def __init__(self):
        self.db_path = config.get("system.research_journal_path", "research_journal.db")
        self._init_db()

    def _init_db(self):
        """Creates the research tables if they don't exist."""
        import os
        abs_path = os.path.abspath(self.db_path)
        logger.info(f"RESEARCH: Initializing database at {abs_path}")
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shadow_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    assets TEXT,
                    direction TEXT,
                    zscore REAL,
                    red_team_audit TEXT,
                    ai_conviction INTEGER,
                    entry_price_a REAL,
                    entry_price_b REAL,
                    outcome TEXT,
                    realized_pnl REAL,
                    slippage_adj_pnl REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_regimes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    macro_context TEXT,
                    ai_interpretation TEXT,
                    realized_volatility REAL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS near_misses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    assets TEXT,
                    reason TEXT,
                    zscore REAL,
                    synthesis TEXT
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("RESEARCH: Database tables verified/created successfully.")
        except Exception as e:
            logger.error(f"RESEARCH: Database initialization FAILED: {e}")

    def log_near_miss(self, miss_data):
        """Logs why a potential setup was rejected (The 'No-Trade' Ledger)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO near_misses (timestamp, assets, reason, zscore, synthesis)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            f"{miss_data['ticker_a']}/{miss_data['ticker_b']}",
            miss_data['reason'],
            miss_data['zscore'],
            miss_data['synthesis']
        ))
        conn.commit()
        conn.close()
        logger.info(f"RESEARCH: Near-Miss logged for {miss_data['ticker_a']}/{miss_data['ticker_b']}")

    def log_shadow_trade(self, trade_data):
        """Logs a paper trade for future post-mortem analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO shadow_trades 
            (timestamp, assets, direction, zscore, red_team_audit, ai_conviction, entry_price_a, entry_price_b)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            f"{trade_data['ticker_a']}/{trade_data['ticker_b']}",
            trade_data['direction'],
            trade_data['zscore'],
            trade_data['audit'],
            trade_data['conviction'],
            trade_data['price_a'],
            trade_data['price_b']
        ))
        conn.commit()
        conn.close()
        logger.info(f"RESEARCH: Shadow Trade logged for {trade_data['ticker_a']}/{trade_data['ticker_b']}")

    def log_regime_interpretation(self, macro_tensor, interpretation):
        """Logs how the AI interpreted the macro environment."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO market_regimes (timestamp, macro_context, ai_interpretation)
            VALUES (?, ?, ?)
        ''', (
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            macro_tensor,
            interpretation
        ))
        conn.commit()
        conn.close()

    def prune_old_data(self, window_days=30):
        """
        Retires research data older than the walk-forward window.
        Prevents Information Decay.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("DELETE FROM shadow_trades WHERE timestamp < ?", (cutoff,))
        cursor.execute("DELETE FROM market_regimes WHERE timestamp < ?", (cutoff,))
        
        conn.commit()
        conn.close()
        logger.info(f"RESEARCH: Pruned data older than {cutoff}.")
