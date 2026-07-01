import os
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

load_dotenv()

def check_alpaca():
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        print("❌ ALPACA: Keys missing in .env")
        return
    
    if "your_key_here" in api_key or "your_key_here" in secret_key:
        print("⚠️  ALPACA: Placeholders detected! Update your .env with real keys from Alpaca Dashboard.")
        return

    if api_key.startswith('"') or api_key.endswith('"'):
        print("⚠️  ALPACA: Key contains quotes. Remove quotes from .env (e.g., KEY=val, not KEY=\"val\")")
    
    try:
        # Use a more descriptive client initialization
        from alpaca.trading.client import TradingClient
        client = TradingClient(api_key, secret_key, paper=True)
        account = client.get_account()
        print(f"✅ ALPACA: Connected. Account Status: {account.status}, Equity: ${account.equity}")
    except Exception as e:
        print(f"❌ ALPACA: Connection failed: {e}")
        print("💡 TIP: Ensure you are using PAPER keys if paper=True, or LIVE keys if paper=False.")


if __name__ == "__main__":
    check_alpaca()
