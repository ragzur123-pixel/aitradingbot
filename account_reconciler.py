import os
import logging
from alpaca.trading.client import TradingClient
from database_manager import TradingDatabase
from utils import setup_logging
from config_loader import config

logger = setup_logging("account_reconciler")

class AccountReconciler:
    """
    Synchronizes Broker (Alpaca) reality with Database (SQLite) records.
    Prevents 'Double Exposure' and 'Trade Amnesia' caused by API glitches.
    """
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.client = TradingClient(self.api_key, self.secret_key, paper=True)
        self.db = TradingDatabase()

    def reconcile_positions(self):
        """Forces the local DB to match the broker's actual open positions."""
        try:
            # 1. Fetch actual open positions from Alpaca
            positions = self.client.get_all_positions()
            broker_assets = [p.symbol for p in positions]
            
            # 2. Fetch 'OPEN' trades from local database
            db_trades = self.db.get_open_trades()
            
            # 3. CRITICAL AUDIT: Identify Ghost Positions
            for trade in db_trades:
                # Ticker translation logic
                db_asset = trade['asset'].split('=')[0].replace("-", "").upper()
                if "/X" in trade['asset'] or "=X" in trade['asset']:
                    base = db_asset[:3]
                    quote = db_asset[3:6]
                    db_asset = f"{base}/{quote}"

                if db_asset not in broker_assets:
                    logger.warning(f"GHOST TRADE DETECTED: DB says {trade['asset']} is OPEN, but Broker says CLOSED. Synchronizing...")
                    self.db.update_trade(trade['asset'], trade['direction'], {"status": "CLOSED", "exit_reason": "RECONCILIATION_SYNC"})
            
            # 4. Identify Unrecorded Positions (Manual trades or API glitches)
            for p in positions:
                # Log them for awareness - we don't auto-add them to DB to avoid logic loops
                # but we warn the orchestrator.
                logger.info(f"POSITION AUDIT: {p.symbol} is currently OPEN with qty {p.qty}")

            return True
        except Exception as e:
            logger.error(f"Account Reconciliation Failed: {e}")
            return False

if __name__ == "__main__":
    reconciler = AccountReconciler()
    reconciler.reconcile_positions()
