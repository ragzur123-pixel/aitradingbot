<div align="center">
 
# AI TRADING BOT
### Autonomous Quantitative & Local LLM Arbitrage Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![Local LLM](https://img.shields.io/badge/AI-Llama_70B-orange?style=flat&logo=meta&logoColor=white)]()
[![ChromaDB](https://img.shields.io/badge/Vector_DB-Chroma-4B4B4B?style=flat)]()
[![Quant](https://img.shields.io/badge/Algorithmic%20Trading-Institutional-black.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*An experimental, multi-modal architecture designed to test local LLM orchestration and fault-tolerant data pipelines in live market conditions.*

</div>

---

## The Engineering Architecture

This project was built from scratch as a 1,700-line system, utilizing LLMs as a coding copilot to rapidly prototype and scale complex infrastructure. Unlike rudimentary indicator bots, this system fuses classical quantitative arbitrage (Pairs Trading, O-U mean reversion) with cutting-edge Local LLM sentiment analysis (Llama 70B). 

- **Intelligent Risk Allocation:** It employs a Bayesian self-auditing mechanic to rigorously calculate probabilities before capital deployment.
- **Institutional Stability:** The architecture includes hard-coded safety gates (correlation vetoes, macro-economic filters, and connection sentinels) to protect capital during black swan events.
- **Defensive Edge:** The engine doesn't just look for entries; it actively finds reasons *not* to trade, preserving capital and generating alpha through rigorous risk management.

---

## System Architecture

The trading bot operates via an asynchronous master orchestrator that manages data ingestion, risk calculation, and market execution.

### Tech Stack
- **Languages**: Python 3.10, Asyncio
- **AI & Models**: Llama-3.1 70B, HuggingFace
- **Data & Databases**: ChromaDB (Vector), SQLite
- **APIs & Integration**: Alpaca, Polygon, DailyFX

```mermaid
graph TD;
  A["Master Orchestrator"] -->|"Triggers"| B("Alpha Queue Scanner");
  A -->|"Spawns"| C["Risk Manager Daemon"];
  B -->|"Mathematical Validation"| D{"Decision Engine"};
  D -->|"Pass"| E["Local LLM Sentiment Audit"];
  D -.->|"Fail: Math Gate"| F["Reject"];
  E -->|"Pass"| G["Alpaca Order Execution"];
  E -.->|"Fail: News Veto"| F;
```

### Algorithmic Execution Flow (Script Interactions)

This detailed pipeline illustrates exactly how the python modules interact during a live trading event. The system heavily prioritizes saving compute and preventing losses by aggressively triggering "Strategic Skips" if any condition is imperfect.

```mermaid
flowchart TD
  %% Define Styles
  classDef core fill:#1E293B,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC
  classDef script fill:#0F172A,stroke:#10B981,stroke-width:1px,color:#F8FAFC
  classDef veto fill:#450A0A,stroke:#EF4444,stroke-width:1px,color:#FEE2E2
  classDef ext fill:#172554,stroke:#60A5FA,stroke-width:1px,color:#DBEAFE
  classDef db fill:#3F3F46,stroke:#A1A1AA,stroke-width:1px,color:#F8FAFC
  
  subgraph "Layer 1: Orchestration (Unified Decision Engine)"
    MO["master_orchestrator.py<br>(Prioritizes Assets, Bayesian Risk Sizing)"]:::core
    RM["risk_manager.py<br>(Deterministic Guardian: Dynamic SL/TP)"]:::script
    DB[("SQLite State DB<br>(atomic_ops.py)")]:::db
    MO -->|"Spawns 5s Daemon"| RM
    RM -->|"Reads/Writes Trade States"| DB
    MO -->|"Reconciles Portfolio Risk"| DB
  end

  subgraph "Layer 2: Execution Pipeline (Subprocess Automation)"
    AP["autonomous_pipeline.py<br>(Clockwork Wrapper)"]:::core
    MS["market_snapshot.py<br>(Pydantic Source-of-Truth)"]:::script
    TB["5_trading_bot.py<br>(Z-Score Arbitrage & Auditor)"]:::script
    CRO["cro_risk.py<br>(Asymmetric Entry Optimizer)"]:::script
  end
  
  MO -->|"Dispatches Target Ticker"| AP
  AP -->|"Subprocess 1"| MS
  MS -->|"If Passes"| TB
  TB -->|"If Passes"| CRO
  
  subgraph "Layer 3: Data & Math Construction"
    MF["market_feed.py<br>(OHLCV, CVD Order Flow, Integrity)"]:::ext
    GEO["geometry.py<br>(FVG, Volume Profile, Sweeps)"]:::ext
    IND["indicators.py<br>(ATR, O-U Reversion, Z-Score)"]:::ext
  end
  
  MS -->|"Fetch Raw Alpaca/Polygon Data"| MF
  MS -->|"Compute SMC Structures"| GEO
  MS -->|"Compute Classic TA"| IND
  MS -.->|"Distance > ATR Threshold"| EXIT_MATH["Zero-Cost Math Gate (Exit 2)"]:::veto
  
  subgraph "Layer 4: Defensive Sentinels & AI"
    GS["global_sentinel.py<br>(DXY, US10Y Vetoes)"]:::veto
    SS["sentiment_sentinel.py<br>(Harvard Consensus NLP)"]:::veto
    LLM["local_llm_client.py<br>(Llama 70B Tensor Evaluation)"]:::ext
    VDB[("ChromaDB<br>(StrategyRetriever)")]:::db
  end
  
  TB -->|"Fetch Past Context"| VDB
  TB -->|"Verify Macro Stability"| GS
  TB -->|"Verify News Sentiment"| SS
  TB -->|"Adversarial Probability Audit"| LLM
  TB -.->|"If Sentinel Detects Risk"| EXIT_VETO["Strategic Veto (Abort)"]:::veto
  
  CRO -->|"Calculates VWAP Limit Order"| ALPACA(("Alpaca DMA")):::ext
```

---

## Core Systems & Sentinels

The bot is divided into highly specialized sentinels and engines:

### Alpha Generation
- **Pairs Arbitrage Scanner**: Scans high-correlation asset pairs (e.g. NVDA vs SOXX) and triggers trades when Z-scores breach standard deviations.
- **Local LLM Sentinel**: Consumes raw numerical order-flow tensors and news headlines via Llama 70B to prevent spoofing and front-running.
- **Regime Classifier**: Determines current market volatility percentiles using ATR to dynamically adjust Stop Loss (SL) and Take Profit (TP) distances.

### Risk Management & Defense
- **VPS Dead-Man's Switch**: A remote Flask server (`deadmans_switch_server.py`) continually monitors a 90-second heartbeat from the local PC. If the local hardware loses power or connectivity, the remote server triggers an emergency liquidation to prevent unmonitored exposure.
- **Global Sentinel**: Pings macro indicators (DXY, VIX, US10Y). If the environment is hostile (e.g., Yield Spike), it issues a hard veto on directional trades.
- **Connectivity Sentinel**: Subprocesses ping checks to exchange servers, blocking trades if network jitter exceeds 350ms.
- **Asymmetric Entry Optimizer**: Rejects immediate execution at the bid/ask spread, actively hunting for VWAP-anchored prices to secure institutional fills.
- **Safety & Testing (Shadow Lock)**: To ensure absolute maturity and safety, the core execution engine is strictly hard-coded into a forward-testing paper simulation lock until May 2027, preventing live capital deployment while safely harvesting out-of-sample performance data.

### State & Persistence
- **ACID-Compliant State Management**: Real-time trade states and portfolio configurations are managed by a custom SQLite implementation (`database_manager.py`). 
- **Thread-Safe File Locking**: To prevent race conditions during high-frequency execution loops, data persistence is protected by a bespoke atomic file lock engine (`atomic_ops.py`).

---

## Quick Start Guide

### Prerequisites
- **Hardware/AI**: Requires Ollama running `llama3.1:70b` on `localhost:11434` and a minimum of 40GB VRAM (for testing on standard machines, you can swap this for a quantized 8B model).
- **Environment**: Python 3.10+

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/ragzur123-pixel/aitradingbot.git
cd aitradingbot
pip install -r requirements.txt
```

### 2. Configuration
Copy the sample config and insert your API keys (Requires free API keys for Alpaca, Polygon.io, and optional Discord/Telegram webhooks for alerts):
```bash
cp config.yaml.example config.yaml
```

### 3. Initialize Vector Database
The system uses ChromaDB for its historical research ingestion. Run the data pipeline to fetch institutional trading lectures from YouTube and feed them directly into the local AI's context window:
```bash
python 1_download_youtube.py
```

### 4. Run the Master Node
Launch the autonomous orchestrator (Runs on an infinite event loop):
```bash
python master_orchestrator.py
```

### 5. Run in Simulation Mode (Safe Demo)
Reviewers and engineers can safely test the quantitative pipeline without real API keys by running the offline backtest simulation:
```bash
python offline_backtest.py
```

---

## About the Developer

This system was built from scratch as an independent learning project. My goal was to teach myself advanced asynchronous Python, fault-tolerant infrastructure, and local AI orchestration. By engineering a complex, event-driven trading environment, I was able to practically explore how different computational systems safely communicate under pressure.

---

## Deep Dive Documentation

For a complete breakdown of every file, mathematical formula, and logic gate used in this system, please read the exhaustive [Master Project Index & Mechanics Map](geminidocs/PROJECT_INDEX.md).

---

## Future Roadmap

This architecture serves as the foundational baseline for a much larger infrastructure build. Future scaling plans include:
- **Advanced LLM Integration**: Upgrading the sentiment analysis engine from local Llama 70B to enterprise-grade APIs (e.g., Anthropic Claude / OpenAI) for deeper, more nuanced macroeconomic reasoning and decision-making.
- **Broker Migration**: Transitioning from Alpaca to IBKR Pro DMA (Direct Market Access) for institutional execution routing.
- **Data Expansion**: Expanding the local ChromaDB vector database to ingest a broader spectrum of global macro-economic reports.
- **Latency Optimization**: Scaling the async orchestrator in Rust or C++ to handle multi-exchange latency arbitrage.

<div align="center">
 <br>
 <i>Built as an exploration of scalable systems engineering and AI orchestration.</i>
</div>
