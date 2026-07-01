import os
import requests
import time
import logging
import psutil
from utils import setup_logging
from notifier import Notifier
from config_loader import config
from database_manager import TradingDatabase

logger = setup_logging("heartbeat_monitor")
notifier = Notifier()
db = TradingDatabase()

class HeartbeatMonitor:
    """
    Central Watchdog to prevent 'Silent Systemic Death'.
    Pings every component and triggers emergency shutdown if critical sensors fail.
    """
    def __init__(self):
        self.critical_services = ["ollama", "alpaca_api"]
        self.check_interval = 30 # 30 seconds

    def check_local_llm(self):
        """Verify Ollama is reachable."""
        try:
            url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/tags")
            res = requests.get(url, timeout=5)
            return res.status_code == 200
        except:
            return False

    def check_alpaca_connectivity(self):
        """Verify Alpaca trading API is responsive."""
        try:
            from alpaca.trading.client import TradingClient
            api_key = os.getenv("ALPACA_API_KEY")
            secret_key = os.getenv("ALPACA_SECRET_KEY")
            client = TradingClient(api_key, secret_key, paper=True)
            account = client.get_account()
            return account.status == 'ACTIVE'
        except:
            return False

    def run_pulse_check(self):
        """Main loop for systemic health."""
        logger.info("Starting Systemic Heartbeat...")
        while True:
            health = {
                "local_llm": self.check_local_llm(),
                "alpaca": self.check_alpaca_connectivity(),
                "timestamp": time.time()
            }

            # If any critical service is down
            if not all(health.values()):
                failed = [k for k, v in health.items() if not v]
                msg = f"🚨 SYSTEMIC FAILURE: Critical services offline: {failed}. TRADING HALTED."
                logger.critical(msg)
                notifier.notify(msg, alert_type="INFO")
                db.set_state("system_health", "CRITICAL_FAIL")
            else:
                db.set_state("system_health", "HEALTHY")
                db.set_state("last_heartbeat", time.time())

            time.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = HeartbeatMonitor()
    monitor.run_pulse_check()
