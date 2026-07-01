import sqlite3
import pandas as pd
import os
import time
from datetime import datetime, timezone, timedelta
from config_loader import config
from tabulate import tabulate

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_db_stats():
    db_path = config.get("system.research_journal_path", "research_journal.db")
    if not os.path.exists(db_path):
        return None
    
    try:
        conn = sqlite3.connect(db_path)
        # Total Trades
        trades_df = pd.read_sql_query("SELECT * FROM shadow_trades", conn)
        conn.close()
        return trades_df
    except Exception as e:
        return None

def get_system_health():
    # Attempt to read from state.json or a shared state
    try:
        from database_manager import TradingDatabase
        db = TradingDatabase()
        health = db.get_state("system_health")
        last_heartbeat = db.get_state("last_heartbeat")
        return health, last_heartbeat
    except:
        return "UNKNOWN", None

def main():
    while True:
        clear_screen()
        print("\n" + "="*70)
        print("      🏛️  OPERATION: TERMINAL ALPHA - INSTITUTIONAL DASHBOARD")
        print("      " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*70)
        
        # 1. SYSTEM HEALTH
        health, last_pulse = get_system_health()
        pulse_str = datetime.fromtimestamp(last_pulse).strftime("%H:%M:%S") if last_pulse else "NEVER"
        health_icon = "🟢" if health == "HEALTHY" else "🔴"
        print(f"STATUS: {health_icon} {health} | LAST PULSE: {pulse_str}")
        print("-" * 70)

        # 2. PERFORMANCE STATS
        trades_df = get_db_stats()
        if trades_df is None or trades_df.empty:
            print("\n[!] No shadow trades logged. Pipeline: ACCUMULATION PHASE.")
            total_pnl = 0.0
            win_rate = 0.0
        else:
            total_pnl = trades_df['slippage_adj_pnl'].sum() if 'slippage_adj_pnl' in trades_df.columns else 0.0
            wins = len(trades_df[trades_df['slippage_adj_pnl'] > 0])
            win_rate = (wins / len(trades_df)) * 100 if len(trades_df) > 0 else 0
            
            print(f"✅ Total Shadow Trades: {len(trades_df)}")
            print(f"✅ Win Rate: {win_rate:.1f}%")
            print(f"✅ Net P&L (Adj): ${total_pnl:+.2f}")
            
            print("\nRECENT ALPHA RESEARCH:")
            last_5 = trades_df.tail(5).copy()
            if not last_5.empty:
                # Format timestamp for display
                last_5['time'] = pd.to_datetime(last_5['timestamp']).dt.strftime('%m-%d %H:%M')
                print(tabulate(last_5[['time', 'assets', 'direction', 'zscore']], headers='keys', tablefmt='psql', showindex=False))

        # 3. FUNDING & LAUNCHPAD
        target_capital = config.get("hustle_fund.target_capital", 10000.0)
        current_savings = config.get("trading.account_balance", 1000.0)
        monthly_injection = config.get("trading.salary_injection_usd", 200.0)
        
        total_fund = current_savings + total_pnl
        remaining = target_capital - total_fund
        
        # Shadow Lock Status
        lock_date_str = config.get("trading.shadow_lock_until", "2027-05-31")
        lock_date = datetime.strptime(lock_date_str, "%Y-%m-%d")
        days_locked = (lock_date - datetime.now()).days
        
        # Launch projection
        months_to_target = remaining / monthly_injection if monthly_injection > 0 else 0
        est_launch_date = datetime.now() + timedelta(days=months_to_target * 30)

        print("\n" + "-"*70)
        print(f"💰 CURRENT TOTAL FUND: ${total_fund:,.2f} / ${target_capital:,.0f}")
        print(f"🎯 PROGRESS: [", end="")
        progress_bars = int((total_fund / target_capital) * 30)
        print("#" * progress_bars + "-" * (30 - progress_bars) + f"] {(total_fund / target_capital) * 100:.1f}%")
        
        print(f"🔒 SHADOW LOCK: {days_locked} Days Remaining (May 2027)")
        print(f"🚀 EST. TARGET HIT: {est_launch_date.strftime('%B %Y')}")
        print("-" * 70)

        if total_fund >= target_capital and days_locked <= 0:
            print("🏆 STATUS: READY FOR INSTITUTIONAL PIVOT (Live IBKR Pro)")
        elif total_fund >= target_capital:
            print("⏳ STATUS: CAPITAL READY - WAITING FOR SHADOW LOCK EXPIRY")
        else:
            print("🛠️  STATUS: ACCUMULATING ALPHA & CAPITAL")

        print("\n[Ctrl+C to Exit] | Refreshing in 60s...")
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDashboard closed.")

