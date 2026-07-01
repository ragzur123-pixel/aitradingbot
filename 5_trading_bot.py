import os
import json
import logging
import sys
import re
import time
import asyncio
import numpy as np
from datetime import datetime, timezone
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from utils import setup_logging
from notifier import Notifier
from market_feed import get_live_market_data, get_macro_context
from local_llm_client import LocalLLMClient
from config_loader import config
from atomic_ops import atomic_read_json, atomic_write_json
from news_sentinel import NewsSentinel
from fundamental_divergence import FundamentalDivergence
from system_health import SystemHealth
from hustle_fund_manager import HustleFundManager
from raw_data_processor import RawDataProcessor
from research_historian import ResearchHistorian
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
logger = setup_logging("trading_bot")
notifier = Notifier()

class StrategyRetriever:
    """Retrieves institutional strategy context from the ingested database."""
    def __init__(self):
        self.db_dir = config.get("database.chroma_dir", "./chroma_db")
        try:
            self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
            self.vector_db = Chroma(persist_directory=self.db_dir, embedding_function=self.embeddings)
            logger.info("Strategy Retriever: ONLINE.")
        except Exception as e:
            logger.error(f"Strategy Retriever Initialization Failed: {e}")
            self.vector_db = None

    def get_strategy_context(self, ticker, query="trading strategy", k=3):
        if not self.vector_db: return "No strategy data available."
        try:
            # Search for ticker-specific or general strategy patterns
            search_query = f"{ticker} {query}"
            docs = self.vector_db.similarity_search(search_query, k=k)
            context = "\n\n".join([f"--- Source Context ---\n{d.page_content}" for d in docs])
            return context
        except Exception as e:
            logger.error(f"Strategy Retrieval Failed: {e}")
            return "Strategy retrieval error."

JOURNAL_PATH = config.get("system.journal_path", "trade_journal.json")

class LogicValidator:
    """Protects against Stale Data, Quantization Hallucinations, and Non-Stationarity."""
    @staticmethod
    def validate_data_freshness(df):
        """Timestamp-Latency Veto: Blocks trades if data is > 30s old."""
        last_time = df.index[-1].to_pydatetime()
        if last_time.tzinfo is None: last_time = last_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delay = (now - last_time).total_seconds()
        if delay > 30:
            return False, f"STALE DATA VETO: {delay:.1f}s delay > 30s limit."
        return True, "Data Fresh"

    @staticmethod
    def validate_arbitrage_math(spread_series):
        """OU Process Veto: Ensures the spread is actually mean-reverting."""
        from indicators import calculate_ou_params
        ou = calculate_ou_params(spread_series)
        if ou['half_life'] > 30:
            return False, f"STATIONARITY VETO: Half-life {ou['half_life']}d > 30d."
        return True, f"OU Validated (HL: {ou['half_life']}d)"

class PreMarketAuditor:
    """
    LLM-Powered Pre-Market Filter.
    Runs at 8:00 AM to generate a 'Forbidden List' of tickers with catalysts.
    Moves LLM latency from Entry-Time to Pre-Market.
    """
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.news_bot = NewsSentinel()
        self.veto_path = config.get("trading.veto_list_path", "forbidden_list.json")

    async def run_audit(self):
        logger.info(f"Initiating Pre-Market Audit for {len(self.portfolio)} tickers...")
        vetoes = {}
        model_name = config.get("models.primary.name", "llama3.1:70b")
        model = LocalLLMClient(model=model_name)

        for ticker in self.portfolio:
            headlines = self.news_bot.get_latest_headlines(ticker)
            if not headlines: continue
            
            prompt = (
                f"TICKER: {ticker}\n"
                f"HEADLINES: {' | '.join(headlines)}\n"
                "TASK: Identify if there is a MAJOR fundamental catalyst today (Earnings, M&A, SEC investigation). "
                "Respond ONLY with 'VETO: [Reason]' if a catalyst exists, or 'CLEAR' if no major event is detected."
            )
            res = await model.ainvoke({"prompt": prompt})
            if "VETO" in res.content:
                vetoes[ticker] = res.content.split("VETO:")[1].strip()
                logger.warning(f"PRE-MARKET VETO for {ticker}: {vetoes[ticker]}")

        atomic_write_json(self.veto_path, vetoes)
        logger.info(f"Pre-Market Audit Complete. {len(vetoes)} tickers forbidden.")

async def run_trading_bot():
    try:
        # --- PHASE 81: THE 12-MONTH SHADOW LOCK ---
        lock_date_str = config.get("trading.shadow_lock_until", "2027-05-31")
        lock_date = datetime.strptime(lock_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        if not config.get("trading.paper_trading", True) and datetime.now(timezone.utc) < lock_date:
            logger.critical(f"SHADOW LOCK VIOLATION: Live trading hard-coded DISABLED.")
            return

        portfolio = config.get("trading.portfolio_tickers", ["TKC", "TUR", "EEM"])
        
        # --- PRE-MARKET AUDIT TRIGGER ---
        now_hour = datetime.now().hour
        pm_hour = config.get("trading.pre_market_veto_hour", 8)
        if now_hour == pm_hour:
            auditor = PreMarketAuditor(portfolio)
            await auditor.run_audit()
            # Return after audit to wait for market open
            return

        # --- INSTANT MATH-FIRST ENTRY ---
        news_bot = NewsSentinel()
        fund_manager = HustleFundManager()
        historian = ResearchHistorian()
        processor = RawDataProcessor()
        retriever = StrategyRetriever()
        health = SystemHealth()

        # 1. System Health Gate
        is_safe, health_report = health.audit_system_readiness()
        if not is_safe:
            logger.critical(f"SYSTEM HEALTH VETO: {health_report['vetoes']}")
            return

        from pairs_trading_scanner import CorrelationArbitrageEngine
        scanner = CorrelationArbitrageEngine()
        
        logger.info("Scanning Niche Portfolio for Arbitrage Anomalies...")
        best_pair = scanner.find_best_pair(portfolio)
        
        z_thresh = config.get("trading.min_zscore_anomaly", 3.5) 
        if not best_pair or abs(best_pair['zscore']) < z_thresh:
            logger.info(f"MATH VETO: No statistical anomaly detected (Z-Score: {best_pair['zscore'] if best_pair else 'N/A'}).")
            return

        ticker_a, ticker_b = best_pair['asset_a'], best_pair['asset_b']
        
        # --- PHASE 85: MACRO-FX VETO (THE CURRENCY GHOST) ---
        divergence_engine = FundamentalDivergence(ticker_a, ticker_b)
        macro_res = divergence_engine.analyze()
        if macro_res and macro_res['signal'] in ["FAKE_DIVERGENCE", "STRUCTURAL_BREAK"]:
            logger.critical(f"MACRO VETO: {macro_res['risk_flags']}")
            return

        # --- PHASE 86: EXECUTION SLIP-CONTROL (SPREAD TAX) ---
        # Assuming we can get spread data from a hypothetical get_market_depth
        # For now, we simulate a 0.5% bid-ask penalty for ADRs
        expected_reversion_pct = abs(best_pair['zscore'] * 0.02) # Crude approximation
        estimated_friction = 0.012 # 1.2% round-trip cost (Spread + Comm + Slippage)
        
        if expected_reversion_pct < estimated_friction:
            logger.warning(f"FRICTION VETO: Alpha ({expected_reversion_pct:.2%}) < Friction ({estimated_friction:.2%}).")
            return

        # 2. Pre-Market Forbidden List Gate
        veto_list = atomic_read_json(config.get("trading.veto_list_path", "forbidden_list.json")) or {}
        if ticker_a in veto_list or ticker_b in veto_list:
            reason = veto_list.get(ticker_a) or veto_list.get(ticker_b)
            logger.warning(f"FORBIDDEN LIST VETO: {reason}")
            return

        # --- PHASE 87: REAL-TIME INTELLIGENCE (LLAMA 70B RE-INTEGRATED) ---
        # Since we are on Daily/H1, the 3s delay is now an asset, not a liability.
        logger.info(f"Initiating Real-Time Adversarial Audit for {ticker_a}/{ticker_b}...")
        headlines = news_bot.get_latest_headlines(ticker_a)
        
        model_name = config.get("models.primary.name", "llama3.1:70b")
        model = LocalLLMClient(model=model_name)
        
        real_time_prompt = (
            f"SIGNAL: {ticker_a} vs {ticker_b} (Z-Score: {best_pair['zscore']})\n"
            f"MACRO_AUDIT: {macro_res}\n"
            f"NEWS: {' | '.join(headlines)}\n"
            "TASK: You are a Risk Manager. Is there an INTRADAY news break or Macro reason to avoid this trade? "
            "Respond ONLY with 'VETO: [Reason]' or 'APPROVED'."
        )
        rt_res = await model.ainvoke({"prompt": real_time_prompt})
        
        if "VETO" in rt_res.content:
            logger.warning(f"REAL-TIME LLM VETO: {rt_res.content}")
            return

        # 3. Execution
        direction_a = "LONG" if best_pair['zscore'] < 0 else "SHORT"
        trade_data = {
            "ticker_a": ticker_a,
            "ticker_b": ticker_b,
            "direction": direction_a,
            "zscore": best_pair['zscore'],
            "audit": "MATH-FIRST INSTANT ENTRY (Pre-Market Filter Passed)",
            "conviction": 10, # High threshold already met by Z-Score 3.5
            "price_a": best_pair['current_a'],
            "price_b": best_pair['current_b']
        }
        historian.log_shadow_trade(trade_data)
        
        msg = (
            f"🚀 <b>INSTANT NICHE ARBITRAGE</b>\n"
            f"Pair: {ticker_a} vs {ticker_b}\n"
            f"Z-Score: {best_pair['zscore']:.2f}\n"
            f"Strategy: Zero-Latency Math Entry\n"
            f"Action: <b>SHADOW LOGGED</b>"
        )
        notifier.notify(msg, alert_type="INFO")
        logger.info(f"SUCCESS: Niche alpha logged for {ticker_a}/{ticker_b}")

    except Exception as e:
        logger.exception(f"Bot crash: {e}")

if __name__ == "__main__":
    asyncio.run(run_trading_bot())
