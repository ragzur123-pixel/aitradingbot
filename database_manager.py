import sqlite3
import json
import logging
from datetime import datetime, timezone
from utils import setup_logging

logger = setup_logging("database_manager")

class TradingDatabase:
    """
    ACID-compliant SQLite database for trade state management.
    Eliminates the corruption risk of raw JSON files.
    """
    def __init__(self, db_path="trading_state.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Trade Journal Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    asset TEXT,
                    direction TEXT,
                    status TEXT,
                    entry_price REAL,
                    qty REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    order_id TEXT,
                    confidence_level INTEGER,
                    outcome TEXT,
                    profit_loss REAL,
                    exit_reason TEXT,
                    full_decision TEXT
                )
            ''')
            # System State Table (KeyValue)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            conn.commit()

    def add_trade(self, trade_data):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades (date, asset, direction, status, confidence_level, full_decision)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                trade_data.get("asset"),
                trade_data.get("direction"),
                "OPEN",
                trade_data.get("confidence_level"),
                trade_data.get("full_decision")
            ))
            conn.commit()
            return cursor.lastrowid

    def update_trade(self, ticker, direction, update_dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Update the latest open trade for this asset/direction
            keys = ", ".join([f"{k} = ?" for k in update_dict.keys()])
            values = list(update_dict.values())
            values.extend([ticker, direction, "OPEN"])
            
            cursor.execute(f'''
                UPDATE trades 
                SET {keys} 
                WHERE asset = ? AND direction = ? AND status = ?
                ORDER BY id DESC LIMIT 1
            ''', values)
            conn.commit()

    def get_open_trades(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_history(self, ticker, limit=5):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE asset = ? ORDER BY id DESC LIMIT ?", (ticker, limit))
            return [dict(row) for row in cursor.fetchall()]

    def set_state(self, key, value):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO system_state (key, value) VALUES (?, ?)", (key, str(value)))
            conn.commit()

    def get_state(self, key, default=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

if __name__ == "__main__":
    db = TradingDatabase()
    db.set_state("bot_status", "ACTIVE")
    print(f"Bot Status: {db.get_state('bot_status')}")
