import os
import json
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
import oandapyV20
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.trades as trades
from utils import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging("watchdog")

JOURNAL_PATH = "trade_journal.json"

class OandaWatchdog:
    def __init__(self):
        self.access_token = os.getenv("OANDA_API_TOKEN")
        self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        if not self.access_token or not self.account_id:
            logger.error("OANDA credentials missing.")
            self.client = None
        else:
            self.client = oandapyV20.API(access_token=self.access_token, environment="practice")

    def close_trade(self, trade_id):
        """Execute immediate market exit for a specific trade ID."""
        if not self.client: return
        r = trades.TradeClose(self.account_id, tradeID=trade_id)
        try:
            self.client.request(r)
            logger.warning(f"OANDA Trade {trade_id} CLOSED by Watchdog.")
            return True
        except Exception as e:
            logger.error(f"Failed to close trade {trade_id}: {e}")
            return False

    def stream_and_monitor(self):
        """Connect to Streaming API and monitor active trades tick-by-tick."""
        if not self.client: return

        logger.info("Starting High-Frequency OANDA Streaming Watchdog...")

        while True:
            try:
                # 1. Identify active trades from journal
                try:
                    with open(JOURNAL_PATH, "r") as f:
                        journal = json.load(f)
                except:
                    time.sleep(10)
                    continue

                active_trades = [t for t in journal if t.get("status") == "OPEN" and "order_id" in t]
                if not active_trades:
                    logger.info("No active OANDA trades. Waiting...")
                    time.sleep(30)
                    continue

                instruments = list(set([t["asset"].replace("=X", "").replace("-", "_").upper() for t in active_trades]))
                params = {"instruments": ",".join(instruments)}
                
                r = pricing.PricingStream(accountID=self.account_id, params=params)
                
                try:
                    for tick in self.client.request(r):
                        if tick["type"] == "PRICE":
                            instrument = tick["instrument"]
                            # Get mid price (average of bid and ask)
                            price = (float(tick["bids"][0]["price"]) + float(tick["asks"][0]["price"])) / 2
                            
                            # Check against active trades for this instrument
                            for trade in active_trades:
                                if trade["asset"].replace("=X", "").replace("-", "_").upper() == instrument:
                                    sl = float(trade["stop_loss"])
                                    direction = trade["direction"]
                                    trade_id = trade["order_id"]
                                    entry_price = float(trade.get("entry_price", 0))
                                    qty = float(trade.get("qty", 0))

                                    trigger_exit = False
                                    if direction == "LONG" and price <= sl: trigger_exit = True
                                    elif direction == "SHORT" and price >= sl: trigger_exit = True

                                    if trigger_exit:
                                        logger.warning(f"!!! STOP LOSS BREACHED !!! {instrument} at {price:.5f}. SL: {sl:.5f}")
                                        if self.close_trade(trade_id):
                                            # Update journal
                                            trade["status"] = "CLOSED"
                                            trade["exit_price"] = price
                                            trade["exit_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            trade["outcome"] = "L"
                                            
                                            # Calculate Profit/Loss
                                            if direction == "LONG":
                                                pl = (price - entry_price) * qty
                                            else:
                                                pl = (entry_price - price) * qty
                                            trade["profit_loss"] = round(pl, 2)

                                            with open(JOURNAL_PATH, "w") as f:
                                                json.dump(journal, f, indent=4)
                                            # Re-scan active trades
                                            break 
                except Exception as e:
                    logger.error(f"Streaming connection lost: {e}. Reconnecting in 5s...")
                    time.sleep(5)
            except Exception as e:
                logger.exception("Fatal crash in WebSocket monitor")
                time.sleep(10)

if __name__ == "__main__":
    watchdog = OandaWatchdog()
    watchdog.stream_and_monitor()
