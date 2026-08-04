import os
import sys

def replace_in_file(path, old, new):
    if not os.path.exists(path):
        print(f"File {path} not found.")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if old in content:
        content = content.replace(old, new)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Replaced in {path}")
    else:
        print(f"String not found in {path}")

os.chdir(r"C:\Users\GranT\OneDrive\Masaüstü\AiTradingBot")

# autonomous_pipeline.py
replace_in_file('autonomous_pipeline.py', 'Strategy: Local-First (Phase 1) + Strategic Alpha', 'Strategy: Local-First + Strategic Alpha')

# deadmans_switch_server.py
replace_in_file('deadmans_switch_server.py', '🚨', '[EMERGENCY]')
replace_in_file('deadmans_switch_server.py', '✅', '[SUCCESS]')

# heartbeat_monitor.py
replace_in_file('heartbeat_monitor.py', '🚨', '[ERROR]')

# market_watcher.py
replace_in_file('market_watcher.py', '# 2. Check for Contrarian Traps (Phase 2026 Alpha)', '# 2. Check for Contrarian Traps')

# offline_backtest.py
replace_in_file('offline_backtest.py', '# Phase 18: Realistic Entry Slippage', '# Realistic Entry Slippage')
replace_in_file('offline_backtest.py', '# Phase 18: Exit Slippage', '# Exit Slippage')

# perpetual_research_monitor.py
replace_in_file('perpetual_research_monitor.py', 'print("\n[!] No shadow trades logged. Pipeline: ACCUMULATION PHASE.")', 'print("\n[!] No shadow trades logged. Pipeline: ACCUMULATION.")')

# setup_linux.sh
replace_in_file('setup_linux.sh', '🏗️', '')
replace_in_file('setup_linux.sh', '✅', '')

# strategy_auditor.py
replace_in_file('strategy_auditor.py', '🚨', '[CRITICAL]')
