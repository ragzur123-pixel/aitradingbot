import json
import os
import logging
from datetime import datetime
from config_loader import config

# Accurate Pricing (2026 Spec)
PRICING = {
    "claude-3-5-sonnet-20240620": {
        "input": 3.00, # Per 1M tokens
        "output": 15.00
    },
    "claude-3-5-haiku-20241022": {
        "input": 0.25,
        "output": 1.25
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.25,
        "output": 1.25
    },
    "gemini-1.5-flash": {
        "input": 0.075,
        "output": 0.30
    }
}

BILLING_FILE = "billing_guard.json"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TOKEN_TRACKER] %(message)s"
)

def track_token_usage(input_tokens, output_tokens, model=None):
    """Log the cost of an API call and update daily spend."""
    if model is None:
        model = config.get("models.consensus_engine", "claude-3-5-haiku-20241022")
        
    model_pricing = PRICING.get(model, PRICING["claude-3-5-haiku-20241022"])
    
    cost = (input_tokens / 1_000_000 * model_pricing["input"]) + (output_tokens / 1_000_000 * model_pricing["output"])
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    data = {}
    if os.path.exists(BILLING_FILE):
        try:
            with open(BILLING_FILE, "r") as f:
                data = json.load(f)
        except: pass
    
    if today not in data:
        data[today] = {"total_cost": 0.0, "total_input_tokens": 0, "total_output_tokens": 0, "calls": 0}
    
    data[today]["total_cost"] += cost
    data[today]["total_input_tokens"] += input_tokens
    data[today]["total_output_tokens"] += output_tokens
    data[today]["calls"] += 1
    
    with open(BILLING_FILE, "w") as f:
        json.dump(data, f, indent=4)
    
    logging.info(f"API Call ({model}) Cost: ${cost:.6f} | Daily Total: ${data[today]['total_cost']:.4f}")
    return data[today]["total_cost"]

def check_killswitch(limit=None):
    """Returns True if the daily spend exceeds the limit."""
    if limit is None:
        limit = config.get("system.token_daily_limit", 2.00)
        
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(BILLING_FILE): return False
    
    try:
        with open(BILLING_FILE, "r") as f:
            data = json.load(f)
        daily_spend = data.get(today, {}).get("total_cost", 0.0)
        if daily_spend >= limit:
            logging.critical(f"KILLSWITCH TRIGGERED: Daily spend ${daily_spend:.2f} exceeds limit ${limit:.2f}")
            return True
    except: pass
    return False

if __name__ == "__main__":
    # Test
    track_token_usage(1000, 500, "claude-3-5-sonnet-20240620")
    l = config.get("system.token_daily_limit", 2.00)
    print(f"Killswitch status (${l} limit): {check_killswitch()}")
