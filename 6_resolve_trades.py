import json
import os

JOURNAL_PATH = "trade_journal.json"

def resolve_trades():
    if not os.path.exists(JOURNAL_PATH):
        print("No trade journal found. Run 5_trading_bot.py first.")
        return

    with open(JOURNAL_PATH, "r") as f:
        try:
            trades = json.load(f)
        except json.JSONDecodeError:
            print("Journal is empty or corrupted.")
            return

    unresolved = [t for t in trades if "outcome" not in t]
    
    if not unresolved:
        print("All trades are already resolved.")
        return

    print(f"Found {len(unresolved)} unresolved trades.")
    
    for trade in unresolved:
        print("\n" + "="*50)
        print(f"Date: {trade['date']}")
        print(f"Asset: {trade['asset']}")
        print(f"Direction: {trade['direction']}")
        print(f"Rationale: {trade['rationale']}")
        print("="*50)
        
        while True:
            outcome = input("Enter outcome (W for Win, L for Loss, S for Skip): ").upper()
            if outcome == 'W':
                trade['outcome'] = "Win"
                break
            elif outcome == 'L':
                trade['outcome'] = "Loss"
                break
            elif outcome == 'S':
                break
            else:
                print("Invalid input. Please enter W, L, or S.")
        
    with open(JOURNAL_PATH, "w") as f:
        json.dump(trades, f, indent=4)
        
    print("\nJournal updated successfully.")

if __name__ == "__main__":
    resolve_trades()
