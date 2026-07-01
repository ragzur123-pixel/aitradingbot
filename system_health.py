import os
import time
import requests
import logging
import platform
import subprocess
import yfinance as yf
from datetime import datetime, timezone
from utils import setup_logging
from notifier import Notifier
from config_loader import config
from pro_data_bridge import ProDataBridge

logger = setup_logging("system_health")
notifier = Notifier()

class SystemHealth:
    """
    Unified System Health Monitor.
    Consolidates Connectivity, Macro Veto, and Heartbeat status.
    Addressing the 'Complexity over Signal' flaw.
    """
    def __init__(self):
        self.pro_bridge = ProDataBridge()
        self.target_host = "api.alpaca.markets"
        self.max_ping_ms = config.get("system.max_ping_ms", 350)
        self.strict_mode = config.get("ingestion.strict_mode", True)

    def check_network_latency(self):
        """Measures network latency (ping) to the broker endpoint."""
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            command = ["ping", param, "1", self.target_host]
            output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
            
            if "Average =" in output: # Windows
                latency = float(output.split("Average =")[1].split("ms")[0].strip())
            else: # Linux/Mac
                latency = float(output.split("/")[-3])
            return latency
        except Exception as e:
            logger.warning(f"Network check failed: {e}")
            return 999

    def get_macro_weather(self):
        """Fetches current state of global lead assets with Strict Mode awareness."""
        weather = {}
        leads = ["DXY", "VIX", "US10Y", "SPY"]
        
        for name in leads:
            # 1. Try Polygon (Primary)
            df = self.pro_bridge.get_macro_data(name)
            
            # 2. Try yfinance (Fallback - Only if NOT in Strict Mode)
            if (df is None or df.empty) and not self.strict_mode:
                logger.info(f"Polygon failed for {name}. Falling back to yfinance (Non-Strict).")
                try:
                    ticker = yf.Ticker(name if name != "DXY" else "DX-Y.NYB")
                    df = ticker.history(period="5d", interval="1h")
                except: continue

            if df is not None and not df.empty:
                latest = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-5] if len(df) >= 5 else df['Close'].iloc[0]
                change = (latest - prev) / prev
                weather[name] = {"price": latest, "5h_change": change}
                
        return weather

    def audit_system_readiness(self, ticker=None, direction=None):
        """
        Comprehensive operational check.
        Returns (is_safe: bool, status_report: dict)
        """
        report = {"status": "STABLE", "vetoes": []}
        
        # 1. Connectivity Check
        latency = self.check_network_latency()
        if latency > self.max_ping_ms:
            report["status"] = "DEGRADED"
            report["vetoes"].append(f"Network Latency: {latency:.0f}ms > {self.max_ping_ms}ms")

        # 2. Macro Weather Check
        weather = self.get_macro_weather()
        if not weather and self.strict_mode:
            report["status"] = "UNSAFE"
            report["vetoes"].append("Macro Sensors Offline (Strict Mode)")
        elif weather:
            # Logic from old GlobalSentinel
            vix_price = weather.get("VIX", {}).get("price", 20)
            if vix_price > 30 and direction == "LONG":
                report["vetoes"].append(f"Global Panic: VIX at {vix_price:.2f}")

            dxy_move = weather.get("DXY", {}).get("5h_change", 0)
            if dxy_move > 0.005 and direction == "LONG" and ticker and ("USD" in ticker):
                report["vetoes"].append(f"DXY Spiking: {dxy_move:.2%} up.")

        # Final Verdict
        is_safe = len(report["vetoes"]) == 0
        if not is_safe:
            logger.warning(f"SYSTEM VETO: {report['vetoes']}")
            
        return is_safe, report

if __name__ == "__main__":
    health = SystemHealth()
    safe, rpt = health.audit_system_readiness("EURUSD", "LONG")
    print(f"Safe: {safe}\nReport: {rpt}")
