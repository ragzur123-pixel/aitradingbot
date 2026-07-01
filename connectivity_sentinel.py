import os
import time
import requests
import logging
import platform
import subprocess
from utils import setup_logging
from notifier import Notifier

logger = setup_logging("connectivity_sentinel")
notifier = Notifier()

class ConnectivitySentinel:
    """
    Monitors local internet quality to Alpaca/Polygon.
    Prevents trading during local 'Jitter' or ISP instability.
    Essential for 24/7 Home Server setups.
    """
    def __init__(self, target_host="api.alpaca.markets"):
        self.target_host = target_host
        self.max_ping_ms = 350 # Max allowed latency for safe execution
        self.max_packet_loss = 0.05 # 5% loss is unacceptable

    def check_latency(self):
        """Measures network latency (ping) in milliseconds."""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "4", self.target_host]
            
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
            
            if "Average =" in output: # Windows
                latency = float(output.split("Average =")[1].split("ms")[0].strip())
            else: # Linux/Mac
                latency = float(output.split("/")[-3])
                
            return latency
        except Exception as e:
            logger.warning(f"Connectivity check failed: {e}")
            return 999 # Fail-safe high latency

    def is_safe_to_trade(self):
        """Audits network health for high-speed execution."""
        latency = self.check_latency()
        
        if latency > self.max_ping_ms:
            logger.warning(f"NETWORK JITTER: Latency is {latency:.0f}ms (Limit: {self.max_ping_ms}ms). Blocking execution.")
            return False, f"High Latency ({latency:.0f}ms)"
        
        return True, "STABLE"

if __name__ == "__main__":
    sentinel = ConnectivitySentinel()
    is_safe, reason = sentinel.is_safe_to_trade()
    print(f"Internet Safe: {is_safe} | Status: {reason}")
