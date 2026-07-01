# AiTradingBot: Final Institutional Index

## 🏗️ System Architecture: The Institutional Hybrid
The AiTradingBot is a multi-strategy, self-evolving quantitative fund. It uses a **Strategic Narrative Model** (H1/H2 timeframe) and is optimized for the **Institutional Launchpad** ($10k+ fund).

### 🕵️ Stealth Protocols & Small-Account Growth
- **Virtual Hidden Stops**: Managed locally by `risk_manager.py` to prevent "Institutional Stop Hunting."
- **Institutional Jitter**: `ibkr_bridge.py` applies randomized Tactical Offsets (0.01-0.05%) to limit prices to avoid HFT detection.
- **Clockwork Operation**: `autonomous_pipeline.py` orchestrates the sequential execution of snapshots and reasoning.
- **Shadow Research Mode**: Hard-locked into paper trading via `research_historian.py` to build a 12-month track record.

---

## 📂 Functional Directory Map

### 1. Portfolio Orchestration & Capital Management
- `master_orchestrator.py`: The System brain. Manages the priority queue and Global Risk.
- `allocator.py`: Manages risk distribution across sub-strategies.
- `global_risk_overlay.py`: Monitors aggregate currency/sector exposure.
- `evolution_engine.py`: Walk-Forward strategy optimizer. Runs weekly post-mortems.
- `priority_queue.py`: Heuristic Alpha Ranker for opportunity prioritization.
- `hustle_fund_manager.py`: Tracks $10k Launchpad goal and 'Prop Firm Readiness'.
- `strategy_auditor.py`: Meta-learning engine for failure audit and bias detection.

### 2. Alpha Sub-Strategies (The "Fund-in-a-Box")
- `contrarian_module.py`: Fades retail traps using liquidity sweep detection.
- `pairs_trading_scanner.py`: Statistical Arbitrage engine for index-basis errors.
- `strategy_library.py`: Formalized playbooks (Trend, Stat-Arb, Contrarian).
- `regime_classifier.py`: Identifies market state (Trending vs Mean-Reverting).
- `bayesian_self_auditor.py`: Uses probability mapping to verify trade confidence.

### 3. Intelligence & Data Ingestion
- `5_trading_bot.py`: Multi-model async reasoning engine with Monte Carlo Consensus.
- `local_llm_client.py`: Bridge to local Llama 3.1 for zero-cost pre-processing.
- `pro_data_bridge.py`: Institutional data interface (Polygon.io).
- `pro_sentiment_engine.py`: High-resolution news-flow urgency analysis.
- `sentiment_sentinel.py`: Multi-source sentiment consensus engine (Harvard Consensus).
- `market_feed.py`: Multi-provider price data ingestion and validation.
- `news_sentinel.py`: Headlines auditor and sentiment divergence detector.
- `cheap_sentiment_scraper.py`: Fallback scraper for retail sentiment.
- `raw_data_processor.py`: Numeric tensor mapper for information preservation.
- `1_download_youtube.py`: RAG ingestion for building the 'Strategy Soul' knowledge base.

### 4. Operational Safety & Monitoring
- `heartbeat_monitor.py` / `heartbeat_sender.py`: watchdog system for systemic health.
- `deadmans_switch_server.py`: Remote fail-safe to liquidate positions on home failure.
- `account_reconciler.py`: Cycle-by-cycle broker-to-DB synchronization.
- `connectivity_sentinel.py`: Latency and jitter auditor (< 350ms ping).
- `token_tracker.py`: Real-time API cost and token consumption auditor.
- `notifier.py`: Unified alert hub (Telegram/Discord) with HITL approval logic.
- `docker-compose.yml` / `Dockerfile`: Containerization and cloud deployment stack.
- `setup_linux.sh` / `aitradingbot.service`: Linux environment provisioning and persistence.
- `windows_watchdog.ps1`: Windows persistence and anti-sleep script.

### 5. Execution & Bridge Modules
- `ibkr_bridge.py`: **DMA Bridge** for IBKR Pro with randomized limit offsets.
- `cro_risk.py`: Alpaca Execution Engine and Order Verification loop.
- `autonomous_pipeline.py`: Asynchronous script runner for the "Clockwork" operation.
- `6_resolve_trades.py`: Post-execution settlement and logging.
- `atomic_ops.py`: Thread-safe file/state operations.

### 6. Math, Research & Verification
- `risk_manager.py`: Advanced risk gate with Dynamic Regime Adaptation.
- `research_historian.py`: SQLite logger for 100% of AI reasoning vs. Reality.
- `offline_backtest.py`: Strategy simulator with slippage penalties.
- `global_sentinel.py`: System-wide state and safety auditor.
- `market_watcher.py` / `price_watch.py`: Real-time price action and level monitors.
- `market_snapshot.py`: Cross-asset market state capture engine.
- `indicators.py`: Technical library (Wilder's RSI, ATR, OU Process).
- `geometry.py`: Euclidean pattern detection and geometric anchors.
- `verify_institutional_setup.py`: System integrity auditor for Launchpad readiness.

---

## 📝 Critical Documentation
- `geminidocs/README.md`: The Path to $100k Capital and Prop Firm readiness.
- `geminidocs/TECHNICAL_API.md`: Detailed function-level reference.
- `geminidocs/SYSTEM_MANIFEST.md`: Level 15 hardening philosophy and "Ground Truth."
- `geminidocs/PROP_FIRM_BRIDGE.md`: Blueprint for DMA migration.
- `PHASE_3_SETUP.md`: Deployment guide for Institutional status.
- `context.md`: Technical hardening and 'Zero-Cost Math Gate' summary.
- `plans.md`: Phase-specific roadmap for geometric precision and hardening.

---
*Last Indexed: 2026-06-01 - Status: Institutional Ready.*
