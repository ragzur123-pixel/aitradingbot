import os
from dotenv import load_dotenv

load_dotenv()

keys = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY", "POLYGON_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
for key in keys:
    val = os.getenv(key)
    if val:
        print(f"{key}: SET (Length: {len(val)})")
    else:
        print(f"{key}: MISSING")
