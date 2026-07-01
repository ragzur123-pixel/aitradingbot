"""
AiTradingBot: Dead-Man's Switch VPS Server
Purpose: Monitors heartbeat from home PC. Closes all Alpaca positions if heartbeat stops.
Usage: Run on a VPS (e.g., Ubuntu).
Requirements: pip install flask alpaca-trade-api
"""

import time
import threading
import logging
from flask import Flask, request, jsonify
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import ClosePositionRequest
import os

# --- CONFIGURATION ---
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
HEARTBEAT_TIMEOUT = 90 # Seconds (3x the sender interval)
PORT = 5000

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DEADMAN_SWITCH")

app = Flask(__name__)
last_heartbeat_time = time.time()
emergency_triggered = False

def close_all_positions():
    """Emergency shutdown command to Alpaca."""
    global emergency_triggered
    if emergency_triggered: return
    
    logger.critical("🚨 HEARTBEAT LOST! TRIGGERING EMERGENCY SHUTDOWN...")
    try:
        client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
        # Close all positions
        client.close_all_positions(cancel_orders=True)
        logger.info("✅ All Alpaca positions closed and orders cancelled.")
        emergency_triggered = True
    except Exception as e:
        logger.error(f"Failed to close positions: {e}")

def watchdog_loop():
    """Background thread that checks the heartbeat clock."""
    global last_heartbeat_time, emergency_triggered
    while True:
        if not emergency_triggered:
            diff = time.time() - last_heartbeat_time
            if diff > HEARTBEAT_TIMEOUT:
                close_all_positions()
        time.sleep(10)

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    global last_heartbeat_time, emergency_triggered
    last_heartbeat_time = time.time()
    if emergency_triggered:
        logger.info("System recovered. Resetting emergency switch.")
        emergency_triggered = False
    return jsonify({"status": "OK", "timestamp": last_heartbeat_time})

if __name__ == "__main__":
    # Start the watchdog thread
    monitor_thread = threading.Thread(target=watchdog_loop, daemon=True)
    monitor_thread.start()
    
    logger.info(f"Dead-Man's Switch active on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT)
