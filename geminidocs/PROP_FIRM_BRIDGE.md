# AiTradingBot: Prop Firm Bridge Blueprint (Launch Day)

## 🎯 Objective
Move the fund from a $1,000 retail-routed Alpaca account to a **$50,000 - $150,000 institutional account** provided by a Prop Firm (Topstep, FTMO).

## 🛠️ Required Infrastructure
To exit the 'Retail Death Trap' on Launch Day, the following stack is required:

### 1. Direct Market Access (DMA) API
- **Primary**: **IBKR Pro API** (via `ib_insync`).
- **Prop-Firm Standard**: **Rithmic API** (Futures) or **MT5 Python API** (CFDs).
- **Why**: Alpaca's PFOF routing will destroy an arbitrage edge. You need to hit the 'Institutional LOB' directly.

### 2. High-Precision Data Feed
- **Primary**: **Polygon.io (SIP Feed)** or **IQFeed**.
- **Requirement**: Must include 'Quote-Level' data (Bid/Ask) and 'Trade-Level' data with millisecond timestamps.
- **Cost**: ~$200/mo (funded by your hustle).

### 3. Dedicated Infrastructure
- **Server**: **Non-Preemptible** GCP/AWS instance in `us-east-1` (NJ Data Centers).
- **GPU**: NVIDIA L4 or higher (Reserved, not Spot).
- **OS**: Headless Linux (Ubuntu 22.04 LTS).

## 📈 Strategic Transition
1.  **Month 1-12**: Shadow Research Mode (current). Logs 100% of trades with 10bps slippage drag into `research_journal.db`.
2.  **Milestone**: Reach +$3,000 shadow profit and $10,000 bank balance.
3.  **The Pivot**:
    - Buy a $50k challenge ($100-$300).
    - Rewrite `cro_risk.py` to target the **MT5/Rithmic API** instead of Alpaca.
    - Set `paper_trading: false` and `broker: IBKR`.

## 📜 Regulatory Note
Trading Prop Firm capital often involves strict 'Trailing Max Drawdown' rules. The `RiskManager.py` must be updated to mirror the Prop Firm's specific liquidation thresholds to prevent manual DQ (Disqualification).
