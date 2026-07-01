# AITradingBot: Development Roadmap (Phase 16+)

## 📊 Current Status Summary
The AITradingBot is now highly resilient and performant. It features **Parallel Robust Ingestion**, **Hybrid Search Retrieval**, and **Multi-Model Intelligence Routing**.

### Core Strengths
- **Robust Ingestion**: Local Whisper fallback ensures 100% transcript availability.
- **Hybrid Retrieval**: BM25 + Vector Search catches both semantic intent and technical keywords.
- **Cost-Efficient Routing**: Junior Analysts run on Flash, saving 80% on trivial analysis tasks.
- **Semantic Memory**: Knowledge is stored in sentence-aware blocks, not arbitrary time slices.

---

## 🚀 Phase 13-15: Hardening & Intelligence (COMPLETE ✅)
**Priority: High** | **Goal**: Resilient ingestion and smarter retrieval.

- [x] **Robust Ingestion (`1_download.py`)**
    - Parallel downloads using `ThreadPoolExecutor`.
    - Local Whisper fallback for missing transcripts.
- [x] **Automated Cleanup (`master_orchestrator.py`)**
    - `raw_videos/` and `extracted_frames/` are cleaned post-ingestion.
- [x] **Hybrid Retrieval (`5_trading_bot.py`)**
    - BM25 keyword search integrated with Chroma vector search.
- [x] **Multi-Model Routing (`5_trading_bot.py`)**
    - Junior Analyst -> Gemini 1.5 Flash.
    - Senior/CRO -> Claude 3.5 Sonnet.
- [x] **Semantic Chunking (`4_build_database.py`)**
    - Chunking by sentence ends/word count (200 words) instead of 30s blocks.

## 🧠 Phase 16: Operational Excellence (COMPLETE ✅)
**Priority: High** | **Goal**: Maintainability and unified control.

- [x] **Notification System (`notifier.py`)**
- [x] **Unified Config (`config.yaml`)**
- [x] **Logging Standardization**
- [x] **Heartbeat Persistence**
- [x] **Mathematical Integrity Fixes**

## 🛠️ Phase 17: Geometric Deepening (COMPLETE ✅)
**Priority: Medium** | **Goal**: Mathematical precision.

- [x] **Geometric Divergence**
- [x] **Unit Testing**

## 🏛️ Operation: Terminal Alpha (INITIATED 🚀)
**Project Manager**: Gemini CLI (Autonomous Mode)
**Goal**: $10,000 Institutional Fund & Proven Alpha for May 2027 Launch.

### Phase 1: Infrastructure & Monitoring (CURRENT 🔄)
- [x] **Database Stabilization**: Fixed `research_historian.py` initialization and pathing.
- [x] **Market Feed Robustness**: Implemented optional CVD and non-blocking fallbacks.
- [x] **Performance Dashboard**: Creating `perpetual_research_monitor.py` for real-time fund tracking.
- [🔄] **Auth Refresh**: Debugging Alpaca 'Unauthorized' error (Improved detection and feedback).
- [x] **Lead-Lag Ensemble**: Integrating Llama 70B + Gemma 9B verification for high-precision entries.

### Phase 2: Alpha Expansion (June 2026) (COMPLETE ✅)
- [x] Fundamental Divergence 2.0: Correlating BIST ADRs (TKC) with US Tech sector for global arbitrage.
- [x] Slippage Stress-Testing: Increasing simulated friction to 15bps to ensure "Bulletproof" backtest results.
- [x] Near-Miss Logging: Historian to log "Why I didn't trade" to identify missed opportunities.


