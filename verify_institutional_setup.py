import os
import requests
import asyncio

# Fix for asyncio event loop in MainThread - MUST BE BEFORE ib_insync import
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from ib_insync import IB
from dotenv import load_dotenv

load_dotenv()

def verify_setup():
    print("--- SYSTEM READINESS CHECK ---")

    # 1. Check Ollama (Llama 3.1)
    try:
        url = "http://localhost:11434/api/tags"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            print("[SUCCESS] OLLAMA: Online")
        else:
            print("[ERROR] OLLAMA: App is running but API returned error.")
    except:
        print("[ERROR] OLLAMA: Not reachable. Is the app running?")

    # 2. Check IBKR Gateway
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=999)
        print("[SUCCESS] IBKR: Connected to Gateway")
        ib.disconnect()
    except:
        print("[ERROR] IBKR: Could not connect to Gateway on port 7497.")

    # 3. Check Polygon API
    poly_key = os.getenv("POLYGON_API_KEY")
    if poly_key:
        try:
            url = f"https://api.polygon.io/v2/last/trade/AAPL?apiKey={poly_key}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                print("[SUCCESS] POLYGON: API Key Valid")
            else:
                print(f"[ERROR] POLYGON: API Error {res.status_code}. Check your key.")
        except:
            print("[ERROR] POLYGON: Network error.")
    else:
        print("[ERROR] POLYGON: Key missing in .env")

if __name__ == "__main__":
    verify_setup()
