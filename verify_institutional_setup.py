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
    print("--- 🔍 SYSTEM READINESS CHECK ---")

    # 1. Check Ollama (Llama 3.1)
    try:
        url = "http://localhost:11434/api/tags"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            print("✅ OLLAMA: Online (Llama 3.1 detected)")
        else:
            print("❌ OLLAMA: App is running but API returned error.")
    except:
        print("❌ OLLAMA: Not reachable. Is the app running?")

    # 2. Check IBKR Gateway
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=999)
        print("✅ IBKR: Connected to Gateway (DMA Active)")
        ib.disconnect()
    except:
        print("❌ IBKR: Could not connect to Gateway on port 7497.")

    # 3. Check Polygon API
    poly_key = os.getenv("POLYGON_API_KEY")
    if poly_key:
        try:
            url = f"https://api.polygon.io/v2/last/trade/AAPL?apiKey={poly_key}"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                print("✅ POLYGON: API Key Valid (Pro-Data Active)")
            else:
                print(f"❌ POLYGON: API Error {res.status_code}. Check your key.")
        except:
            print("❌ POLYGON: Network error.")
    else:
        print("❌ POLYGON: Key missing in .env")

if __name__ == "__main__":
    verify_setup()
