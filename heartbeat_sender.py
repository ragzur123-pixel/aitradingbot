import os
import time
import requests
import logging
from dotenv import load_dotenv
from utils import setup_logging

load_dotenv()
logger = setup_logging("heartbeat_sender")

class HeartbeatSender:
    """
    Runs on the local home PC. 
    Pings the VPS Dead-Man's Switch server every 30 seconds.
    """
    def __init__(self, vps_url=None):
        self.vps_url = vps_url or os.getenv("DEADMAN_SWITCH_URL")
        self.interval = 30 # Seconds

    def send_heartbeat(self):
        if not self.vps_url:
            logger.warning("DEADMAN_SWITCH_URL not set. Heartbeat disabled.")
            return

        logger.info(f"Starting heartbeat sender to {self.vps_url}...")
        while True:
            try:
                response = requests.post(f"{self.vps_url}/heartbeat", json={"status": "ALIVE"}, timeout=10)
                if response.status_code == 200:
                    logger.debug("Heartbeat delivered successfully.")
                else:
                    logger.warning(f"Heartbeat failed with status: {response.status_code}")
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
            
            time.sleep(self.interval)

if __name__ == "__main__":
    sender = HeartbeatSender()
    sender.send_heartbeat()
