# AITradingBot: Technical System Architecture (Hardened Production)

## 1. Core Orchestration & Lifecycle

### `master_orchestrator.py`
The "Brain" of the system. Manages long-running background services and the main trading loop.
- **UTC Integrity**: Enforces strict `timezone.utc` for all logs and state persistence to match Alpaca standards.
- **`start_background_process`**: Uses `psutil` to ensure singleton instances of critical services like `risk_manager.py`. Prevents resource contention.
- **Main Loop**:
    - **Token Burn Killswitch**: Calls `token_tracker.check_killswitch()` before every cycle. Halts if daily budget (default $2.00) is exceeded.
    - **Heartbeat Persistence**: Updates `state.json` with `total_cycles`, `last_cycle_duration`, and `avg_cycle_duration` for system health monitoring.
    - **Automated Cleanup**: Triggers `cleanup_processed_data` to remove ephemeral artifacts.

### `autonomous_pipeline.py`
The "Task Runner". Executes sequential steps of a single trading cycle.
- **Integrity Gate**: If `market_snapshot.py` returns `False` (Math Gate closed) or any script fails, the operation halts immediately.

---

## 2. Data Ingestion & Vision Pipeline

### `market_feed.py`
The "Strict Data Provider".
- **Alpaca-Only Routing**: Strictly fetches official exchange data via specialized clients (`StockHistoricalDataClient`, `ForexHistoricalDataClient`).
- **Data Integrity**: Zero tolerance for delayed data. If Alpaca keys or feeds are unavailable, the bot halts.
- **Staleness Guard**: Logs critical alerts if data is >24h old during trading sessions.

---

## 3. Intelligence & Signal Generation

### `market_snapshot.py`
The "Source of Truth" & Cost Guard.
- **Zero-Cost Math Gate**: Uses pure Python/Pandas to check if price is within 0.2% of a Swing High/Low or tapping an FVG. Aborts pipeline *before* AI calls if no setup exists.
- **Pydantic Validation**: Strictly enforces data types and range limits for RSI, ATR, and price evidence.

### `sentiment_sentinel.py`
The "Sonnet-Powered" Oracle.
- **Consensus Voting**: Weighted voting between Retail (DailyFX), Institutional (COT), and News.
- **Sonnet 3.5 Upgrade**: Uses Claude-3.5-Sonnet for high-precision macro sentiment analysis.
- **Reliability Fail-Safe**: Nullifies bias (0.0) if sentiment sources are offline or fragmented.

---

## 4. Execution & Risk Management

### `5_trading_bot.py`
The "Decision Engine".
- **Multi-Model Routing**: Junior Analyst (Flash) -> Senior/CRO (Sonnet 3.5).
- **Thresholded Retrieval**: `HybridRetriever` uses a 0.65 similarity threshold to filter noise from `chroma_db`.
- **Kelly Criterion**: Uses calibrated Bayesian probabilities and Half-Kelly logic for sizing.

### `cro_risk.py`
The "Hardened Executioner".
- **ATR Dynamic Risk**: Calculates Stop Loss at 1.5 * ATR and Take Profit at 3.0 * ATR for volatility-adjusted protection.
- **Order Verification**: Asynchronous polling loop (60s) verifies order `FILLED` status before trade journaling.
- **Buying Power Audit**: Verifies `non_marginable_buying_power` before order submission.

---

## 5. Utility & Safety Layers

### `indicators.py`
Mathematical library.
- **Wilder's Smoothing (SMMA)**: RSI and ATR implemented with industry-standard SMMA smoothing to match TradingView/MT4 precision.
- **EMA**: Standard `ewm` implementation.

### `geometry.py`
- **Euclidean Distance**: Measures precise price proximity to swing levels for "Liquidity Trap" detection.
