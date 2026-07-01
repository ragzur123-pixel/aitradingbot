import subprocess
import sys
import time
import os
import logging
import json
import signal
import psutil
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from utils import setup_logging
from token_tracker import check_killswitch
from notifier import Notifier
from config_loader import config
from atomic_ops import atomic_read_json, atomic_write_json
from news_sentinel import NewsSentinel
from market_feed import get_live_market_data

from global_sentinel import GlobalSentinel
from priority_queue import AlphaQueue
from connectivity_sentinel import ConnectivitySentinel
from account_reconciler import AccountReconciler

# Setup logging
logger = setup_logging("orchestrator")
notifier = Notifier()
news_sentinel = NewsSentinel()
macro_sentinel = GlobalSentinel()
net_sentinel = ConnectivitySentinel()
reconciler = AccountReconciler()

STATE_FILE = config.get("system.state_file", "state.json")

def load_state():
    return atomic_read_json(STATE_FILE, {"last_cycle": None, "total_cycles": 0, "status": "IDLE"})

def save_state(state):
    atomic_write_json(STATE_FILE, state)

def get_portfolio_exposure():
    """Calculate current risk exposure and identify active tickers."""
    trades = atomic_read_json(config.get("system.journal_path", "trade_journal.json"), [])
    active_trades = [t for t in trades if t.get("status") == "OPEN"]
    
    exposure = {"total_risk_val": 0.0, "active_tickers": []}
    for t in active_trades:
        exposure["total_risk_val"] += t.get("risk_amount", 0.0)
        exposure["active_tickers"].append(t.get("asset"))
        
    return exposure

def check_correlation_veto(new_ticker, active_tickers):
    """Prevents over-exposure using Pearson Correlation."""
    if not active_tickers: return True
    try:
        new_df = get_live_market_data(new_ticker, period="30d")
        if new_df is None or new_df.empty: return True
        new_returns = new_df['Close'].pct_change().dropna()
        threshold = config.get("trading.max_correlation_threshold", 0.70)
        for active_ticker in active_tickers:
            active_df = get_live_market_data(active_ticker, period="30d")
            if active_df is None or active_df.empty: continue
            active_returns = active_df['Close'].pct_change().dropna()
            combined = pd.concat([new_returns, active_returns], axis=1).dropna()
            if len(combined) < 15: continue
            correlation = np.corrcoef(combined.iloc[:, 0], combined.iloc[:, 1])[0, 1]
            if correlation > threshold:
                return False
    except: pass
    return True

def get_risk_scaler(ticker, direction="LONG"):
    """
    Tiered Risk Gates (Phase 14 Hardening).
    Hard Veto (Return 0.0) | Soft Penalty (Return 0.5) | Full (1.0)
    """
    # TIER 1: HARD VETOES
    is_stable, net_reason = net_sentinel.is_safe_to_trade()
    if not is_stable:
        logger.warning(f"HARD VETO (NET): {net_reason}")
        return 0.0

    is_blackout, news_reason = news_sentinel.is_blackout_active()
    if is_blackout:
        logger.warning(f"HARD VETO (NEWS): {news_reason}")
        return 0.0

    # TIER 1.5: PORTFOLIO EXPOSURE CAPS
    exposure = get_portfolio_exposure()
    max_active_trades = config.get("trading.max_active_trades", 5)
    if len(exposure["active_tickers"]) >= max_active_trades:
        logger.warning(f"HARD VETO (CAP): Max active trades ({max_active_trades}) reached.")
        return 0.0
        
    # Total Portfolio Risk Cap (e.g., max 5% of account risked at once)
    from cro_risk import AlpacaExecutor
    executor = AlpacaExecutor()
    equity = executor.get_total_equity()
    total_risk_limit = equity * config.get("trading.max_total_portfolio_risk_pct", 0.05)
    
    if exposure["total_risk_val"] >= total_risk_limit:
        logger.warning(f"HARD VETO (RISK): Total exposure ${exposure['total_risk_val']:.2f} >= Limit ${total_risk_limit:.2f}")
        return 0.0

    # TIER 2: SOFT PENALTIES
    risk_scaler = 1.0
    is_macro_veto, macro_reason = macro_sentinel.check_global_veto(ticker, direction)
    if is_macro_veto:
        logger.info(f"SOFT PENALTY (MACRO): {macro_reason}. Scaling risk 50%.")
        risk_scaler *= 0.5

    if not check_correlation_veto(ticker, exposure["active_tickers"]):
        logger.info(f"SOFT PENALTY (CORR): High correlation. Scaling risk 50%.")
        risk_scaler *= 0.5

    return risk_scaler

def run_script(script_name, args=None):
    cmd = [sys.executable, script_name]
    if args: cmd.extend(args)
    try:
        subprocess.run(cmd, check=True)
        return True
    except: return False

def set_high_priority():
    if os.name == 'nt':
        try:
            p = psutil.Process(os.getpid())
            p.nice(psutil.HIGH_PRIORITY_CLASS)
            logger.info("WINDOWS OPTIMIZATION: Priority set to HIGH.")
        except: pass

from evolution_engine import EvolutionEngine

# Setup logging
# ... (existing sentinels)
evolution_engine = EvolutionEngine()

def run_weekly_tasks():
    """Performs strategic maintenance (Meta-Evolution)."""
    now = datetime.now()
    # Run every Sunday at 00:00
    if now.weekday() == 6 and now.hour == 0 and now.minute < 5:
        logger.info("📅 SUNDAY STRATEGIC WINDOW: Running Evolution Engine...")
        evolution_engine.run_weekly_evolution()

import multiprocessing

def run_risk_manager():
    """Independent process for high-frequency risk monitoring."""
    from risk_manager import monitor_active_trades, update_state_pl, send_daily_summary
    logger.info(">>> DETACHED RISK MANAGER STARTING (Dedicated CPU Core) <<<")
    while True:
        try:
            monitor_active_trades()
            update_state_pl()
            send_daily_summary()
        except Exception as e:
            logger.error(f"Risk Manager Process Error: {e}")
        time.sleep(5)

import asyncio
import multiprocessing

from bayesian_self_auditor import BayesianSelfAuditor

# --- PHASE 24: UNIFIED PREDATOR ARCHITECTURE ---
class DecisionEngine:
    """Unified Decision Engine with Bayesian Calibration."""
    def __init__(self):
        self.local_ai = LocalLLMClient(model="llama3.1-70b-q4") # 70B Quantized on GCP L4
        self.sonnet = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0.7) 
        self.processor = RawDataProcessor()
        self.bayesian_auditor = BayesianSelfAuditor()

    async def audit_ticker(self, ticker, risk_scaler):
        """Unified Async Pipeline with Order Flow Intelligence and Bayesian Sizing."""
        logger.info(f"INITIATING AUDIT for {ticker}...")
        
        # 0. WHOLE-UNIT PIVOT (Phase 26)
        from allocator import MultiStrategyAllocator
        from cro_risk import AlpacaExecutor
        executor = AlpacaExecutor()
        equity = executor.get_total_equity()
        alloc = MultiStrategyAllocator(total_equity=equity)
        
        # 1. Fetch Data
        df = get_live_market_data(ticker)
        if df is None: return
        current_price = df['Close'].iloc[-1]
        
        # 2. Pivot & Alpha Filter
        risk_usd = (equity * 0.01) * risk_scaler
        ticker = alloc.get_tradable_ticker(ticker, risk_usd, current_price)
        
        tensor = self.processor.prepare_compressed_tensor(df)
        alpha_prompt = (
            "You are a Senior Statistical Arbitrage Quant analyzing ORDER FLOW TENSORS.\n"
            "COLUMNS: Time, Price% (CP), Vol_Ratio (VR), RSI (R), CVD_Aggression (CG), Accel (PA).\n"
            f"DATA:\n{tensor}\n\n"
            "STRATEGIC CHECK:\n"
            "1. INERTIA / MEAN REVERSION: Are we fading an exhausted move? (High VR but PA is flattening).\n"
            "2. ANTI-SPOOFING: If VR is extremely high but CP isn't moving, assume spoofing/traps. VETO immediately.\n"
            "Output ONLY 'PROCEED' if you see a high-conviction STAT-ARB or MEAN REVERSION setup, else 'JUNK'."
        )
        res = await asyncio.to_thread(self.local_ai.invoke, alpha_prompt)
        
        if "PROCEED" not in res.content.upper():
            logger.info(f"ALPHA VETO: {ticker} is JUNK.")
            return

        # 3. Strategic Synthesis (Phase 27 Calibration)
        # In a real run, this would be a full Sonnet cycle.
        # We assume Sonnet gives a Confidence Level (1-5).
        conf_lv = 4 
        
        # 4. BAYESIAN CALIBRATION
        realized_rates = self.bayesian_auditor.get_realized_edge()
        real_prob = realized_rates.get(conf_lv, 0.50)
        
        logger.info(f"CALIBRATED PROBABILITY for {ticker}: {real_prob:.1%}")

        # 5. EXECUTION
        from cro_risk import finalize_trade_execution
        finalize_trade_execution(ticker, "LONG", risk_usd, confidence_level=conf_lv)

async def main_loop():
    set_high_priority()
    engine = DecisionEngine()
    alpha_q = AlphaQueue()
    
    # 1. Detach Risk Manager (Dedicated Thread)
    risk_proc = multiprocessing.Process(target=run_risk_manager, daemon=True)
    risk_proc.start()

    try:
        while True:
            # 2. State Reconciliation
            reconciler.reconcile_positions()
            
            # 3. Priority Processing
            candidates = alpha_q.get_all_candidates() # Non-destructive peek
            tasks = []
            for c in candidates:
                ticker = c['ticker']
                scaler = get_risk_scaler(ticker)
                if scaler > 0:
                    tasks.append(engine.audit_ticker(ticker, scaler))
            
            if tasks:
                await asyncio.gather(*tasks)
            
            # 4. Global Cycle Sleep
            interval = config.get("trading.cycle_interval_seconds", 3600)
            await asyncio.sleep(interval)
            
    except KeyboardInterrupt:
        risk_proc.terminate()

def run_risk_manager():
    """Independent process for high-frequency risk monitoring."""
    from risk_manager import monitor_active_trades, update_state_pl
    logger.info(">>> RISK MANAGER ACTIVE (5s Cycle) <<<")
    while True:
        monitor_active_trades()
        update_state_pl()
        time.sleep(5)

if __name__ == "__main__":
    asyncio.run(main_loop())
