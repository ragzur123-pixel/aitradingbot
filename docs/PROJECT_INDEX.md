# AiTradingBot - Master Project Index & Internal Mechanics Map (Extreme Detail Edition)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Quant](https://img.shields.io/badge/Quant-Algorithmic_Trading-000000?style=for-the-badge&logo=python)
![Machine Learning](https://img.shields.io/badge/AI-Llama_70B-orange?style=for-the-badge&logo=meta)

This document provides an exhaustive, extremely detailed plain-text breakdown of the AiTradingBot architecture. It explains precisely what each file is doing at a mechanical and mathematical level, mapping out the internal code flows, variables, and logic gates of the trading pipeline.

---

## Investment Thesis (Funding & Scalability)

This system is engineered as an autonomous, multi-modal quantitative trading engine designed to outmaneuver standard retail execution. 

* **Why Fund This Project?** Unlike rudimentary indicator bots, this system fuses classical quantitative arbitrage (Pairs Trading, O-U mean reversion) with cutting-edge Local LLM sentiment analysis (Llama 70B). It employs a bayesian self-auditing mechanic to rigorously calculate probabilities before capital deployment.
* **Scalability:** The architecture is decoupled, scalable, and built for institutional stability. It includes hard-coded safety gates (correlation vetoes, macro-economic filters, and connection sentinels) to protect capital during black swan events.
* **Defensive Edge:** The engine doesn't just look for entries; it actively finds reasons *not* to trade, preserving capital and generating alpha through rigorous risk management and systemic auditing.

---

## 1. Core Orchestration & Automation

### master_orchestrator.py (Master Process & Unified Decision Engine)
**What the code is actively doing:**
This is the top-level orchestration daemon for the trading system, responsible for prioritizing assets, checking systemic risk gates, and scheduling independent operational processes.
- **Execution Flow:** 
 The script initializes by applying a Windows-specific OS priority optimization (`set_high_priority`) to ensure execution is uninterrupted. It then spawns a separate multiprocessing daemon thread (`run_risk_manager`) dedicated entirely to tracking active trades. 
 In the primary asynchronous `main_loop()`, the orchestrator continuously reconciles account positions, pops trading candidates from the `AlphaQueue`, and applies tiered risk-sizing rules. For candidates that pass the initial risk gates, it launches the unified `DecisionEngine.audit_ticker()` pipeline via `asyncio.gather`. The script then puts the cycle to sleep for a configurable interval (default 3600 seconds) before repeating.
- **Internal Functions:**
 - `load_state()` / `save_state()`: Handles atomic JSON reads/writes to track lifetime execution metadata.
 - `get_portfolio_exposure()`: Scans the JSON trade journal to sum the active open risk amount (`total_risk_val`) and logs the active tickers.
 - `check_correlation_veto(new_ticker, active_tickers)`: Prevents deploying capital into highly correlated assets.
 - `get_risk_scaler(ticker, direction)`: The Phase 14 Hardening core logic. Implements Tier 1 "Hard Vetoes" (connectivity issues, news blackouts, active trade caps, or max portfolio risk breached) returning a scaler of `0.0`. Implements Tier 2 "Soft Penalties" where global macro headwinds or high correlation cut the baseline risk multiplier (`1.0`) by 50% (`0.5`).
 - `run_weekly_tasks()`: A scheduled meta-evolution routine that runs only at 00:00 on Sundays.
 - `DecisionEngine.audit_ticker()`: Pulls a candidate ticker, computes risk value based on account equity, formats market order flow into a compressed data tensor, and queries a local Llama-3.1 70B model. It evaluates "Inertia/Mean Reversion" and "Anti-Spoofing" traits. Uses a Bayesian Auditor to pull a historically calibrated probability of success before triggering the execution phase.
- **Mathematical Formulas:**
 - **Pearson Correlation (Veto):** `np.corrcoef(new_returns, active_returns)[0, 1] > 0.70` calculated over a 30-day percentage change data frame.
 - **Total Portfolio Risk Cap:** Hard veto triggered if `total_risk_val >= (equity * 0.05)`.
 - **Calibrated Probability:** Retrieves a realized edge rate (e.g., 0.50) based on historical confidence intervals via the `BayesianSelfAuditor`.
- **Variables:** `total_risk_val`, `active_tickers`, `risk_scaler`, `risk_usd`, `real_prob`, `conf_lv`.

### autonomous_pipeline.py (Sequential Clockwork Automation)
**What the code is actively doing:**
Acts as a rigid pipeline wrapper to sequentially execute a localized list of modular scripts ("CLOCKWORK Operations").
- **Execution Flow:** 
 Given a specific `ticker` argument (defaults to "EURUSD=X"), the script iterates over a predefined list of scripts (`market_snapshot.py`, `5_trading_bot.py`). It uses `asyncio.create_subprocess_exec` to spawn subprocesses and awaits their completion. It evaluates the process exit codes to determine the pipeline's fate:
 - Exit `0`: Proceed to the next script.
 - Exit `2`: Represents a deliberate "STRATEGIC SKIP" (e.g., a math gate blocked the trade, yielding no alpha). The pipeline gracefully stops to save compute cost.
 - Any other exit: Represents a critical error, dumping stderr to the logs and aborting the program.
- **Internal Functions:**
 - `run_script_async(script, ticker)`: Handles the subprocess execution, captures stdout/stderr buffers, evaluates the return code, and propagates errors.
 - `run_operation(ticker)`: Main event loop measuring pipeline execution duration and terminal logging.
- **Mathematical Formulas:** None directly present; strictly handles I/O and process status codes.
- **Variables:** `scripts` (list of python files), `exit_code`, `start_time`, `duration`.

### 5_trading_bot.py (Zero-Latency Arbitrage & Adversarial Entry Auditor)
**What the code is actively doing:**
This is the core "Alpha generation" and filtering brain. It operates an instant math-first entry model shielded by pre-market audits, structural latency filters, and real-time LLM intelligence to sniff out anomalies.
- **Execution Flow:** 
 Inside `run_trading_bot()`, the script first enforces a "Shadow Lock" hardcode (preventing live trading until May 2027 to force paper-testing). At 8:00 AM, it triggers the `PreMarketAuditor` to pre-generate a list of "forbidden" tickers possessing negative news catalysts.
 In active scanning, it checks `SystemHealth`, then uses the `CorrelationArbitrageEngine` to scan the portfolio for a viable math anomaly pair. It then sequentially applies macroeconomic vetoes, execution friction calculations, and the forbidden list veto. Finally, it uses a real-time LLM (Llama 70B) to adversarially review the candidate, fundamental data, and fresh news. If it survives, it shadow-logs the trade to the database.
- **Internal Functions:**
 - `StrategyRetriever`: Queries a local Chroma Vector Database via `HuggingFaceEmbeddings` to extract historically ingested institutional context for a ticker.
 - `LogicValidator.validate_data_freshness()` / `validate_arbitrage_math()`: Blocks trades where the data packet is older than 30s, or the Ornstein-Uhlenbeck mean-reversion half-life is greater than 30 days.
 - `PreMarketAuditor.run_audit()`: Polls news sentinels and builds a localized `forbidden_list.json` by prompting an LLM about fundamental catalysts.
- **Mathematical Formulas:**
 - **Z-Score Filter:** Enforces a rigid statistical threshold anomaly (`min_zscore_anomaly = 3.5`).
 - **Friction/Spread Tax:** Checks if `expected_reversion_pct < estimated_friction`. Expected reversion is approximated as `abs(zscore * 0.02)`, and friction is assumed fixed at `0.012` (1.2% covering spread, commissions, slippage).
- **Variables:** `z_thresh`, `expected_reversion_pct`, `estimated_friction`, `lock_date`, `trade_data`.

### cro_risk.py (Alpaca Execution & Asymmetric Order Routing)
**What the code is actively doing:**
Acts as the Chief Risk Officer (CRO) of execution. It maps mathematical logic directly into live exchange endpoints using the Alpaca API. Its primary goal is manipulating order structures to avoid PFOF (Payment for Order Flow) taxes and institutional stop-hunting.
- **Execution Flow:** 
 Instead of hurling market orders, the system relies on `finalize_trade_execution()`. It extracts an initial target price from `market_snapshot.md`, then hands control to the `AsymmetricEntryOptimizer` to aggressively hunt for a superior VWAP-anchored price over a window of several minutes. Once an entry price is locked, it dynamically computes Stop Loss and Take Profit distances, calculates total shares (`qty`), and executes a `Passive Maker Limit` order inside the bid-ask spread to collect liquidity.
- **Internal Functions:**
 - `AlpacaExecutor`: Wrapper for the API. Includes an automated `verify_order_fill` polling loop to prevent "Execution Blindness" if an order isn't actually filled.
 - `execute_passive_maker_entry()`: Exploits maker-taker mechanics by setting limits embedded inside the spread natively.
 - `AsymmetricEntryOptimizer.calculate_vwap()` & `get_optimal_fill_price()`: Avoids immediate hour-boundary entries. It monitors 1-minute candles for up to 15 minutes waiting for price to touch the 1-minute VWAP to secure institutional fills, with an emergency "chase" threshold to catch explosive breakouts.
 - `AggressiveLimitEntry.get_tactical_limit_fill()`: Drops a limit order `0.2%` below the price to purposefully catch wicks.
- **Mathematical Formulas:**
 - **VWAP Calculation:** `(Price * Volume).cumsum() / Volume.cumsum()`, where `Price = (High + Low + Close) / 3`.
 - **Maker Buffer Pricing:** Limit price shifted inward by `-2.0` basis points: `limit_price = current_price +/- (current_price * (abs(-2.0) / 10000))`.
 - **Default Stop Sizing:** Fixed distance multiplier for entries without manual stops (1.5% SL, 4.5% TP). Stop Loss = `entry_price * (1 +/- 0.015)`.
 - **Position Sizing Engine:** `Qty = int(risk_val / abs(entry_price - stop_loss))`.
- **Variables:** `maker_buffer_bps`, `chase_threshold`, `risk_per_share`, `qty`.

### risk_manager.py (Deterministic Guardian & Microstructure Adjustments)
**What the code is actively doing:**
An infinite-loop watchdog operating out-of-band on a 5-second frequency. Its sole job is to secure open positions, analyze dynamic market volatility, and sever trades virtually without exposing stop-loss parameters on public order books.
- **Execution Flow:** 
 The main loop executes `monitor_active_trades()`, `update_state_pl()`, and `send_daily_summary()`. For every active trade inside the trade journal, it fetches fresh ticker data and checks current pricing against mathematically computed virtual limits. If a price boundary is crossed, it overrides normal operations and blasts a `close_position` payload directly to the broker API, then securely writes the closed trade state.
- **Internal Functions:**
 - `update_state_pl()` & `send_daily_summary()`: Tallies historical lifetime P/L and texts the admin a daily ledger recap after 8:00 PM.
 - `check_market_regime(df)`: Uses average directional index indicators to vet if the market is trending heavily or chopping.
 - `DynamicRegimeClassifier.get_regime_multipliers(df)`: Contextualizes current market fear levels by calculating the historical percentiles of the True Range.
 - `calculate_deterministic_risk_levels()`: Implements advanced volume profile anchoring to build optimal exit parameters natively.
- **Mathematical Formulas:**
 - **ADX Filter:** Vetoes trades if `ADX_14 < 20`.
 - **Regime Multipliers:** Calculates ATR percentage: `atr_pct = (ATR / Close) * 100`. Compares the current ATR to a 100-period history to find its percentile rank (`p_rank`). 
  - `< 30th Percentile` (Low Volatility): `SL = 1.8x, TP = 4.0x`.
  - `> 80th Percentile` (High Volatility/Panic): `SL = 3.5x, TP = 2.5x`.
 - **Dynamic Anchoring:** Calculates distance `sl_dist = max(atr * sl_mult, v_floor * 3.0)`. If a Volume Profile Point of Control (POC) exists tightly within the stop zone, it logically shifts the stop loss directly behind it: `sl = POC +/- (v_floor * 1.5)`.
- **Variables:** `adx`, `atr_pct`, `p_rank`, `sl_dist`, `v_floor`, `va_high`, `poc`.

### offline_backtest.py (Historical Crucible Engine)
**What the code is actively doing:**
An offline simulator used to mathematically stress-test and refine the AI's internal risk calculators over large sets of historical data, bypassing real-money interactions. It explicitly penalizes the bot with synthetic latency taxes to replicate hostile real-world brokerage exchanges.
- **Execution Flow:** 
 Downloads multi-day historical data segments (15-min intervals) using `yfinance`. Iterates sequentially bar by bar, behaving precisely like a forward-walking event loop. Every simulated 4-hours (16 periods), it "wakes the LLM" mimicking a trade signal decision. It tests risk validation parameters natively, places simulated active trades directly into state memory, updates them tick-by-tick against dynamic trailing stops, applies slippage math to the exits, aggregates the final P/L, and logs an equity curve summary.
- **Internal Functions:**
 - `StrategySimulator.simulate_trade()`: Generates the mock trade state.
 - `StrategySimulator.update()`: Computes High/Low water marks as new bars load and tracks if trailing limits or SL/TP targets were met. Applies real exit modifiers and records closed deals.
 - `run_backtest()`: Orchestrates the data ingest, indicator formatting, loop iteration, and prints the simulated ledger.
- **Mathematical Formulas:**
 - **Realistic Entry Slippage (Friction Factor):** Computes a synthetic tax on the entry fill based on predefined basis points (e.g., 2.0 bps spread + 2.5 bps latency = 4.5 bps total). `friction_factor = 1 + (4.5 / 10000)`.
 - **Simulated Limits:** Stop Loss locked at `ATR * 1.5`. Take Profit locked at `ATR * 3.0`.
 - **ATR Trailing Stop:** Tracks the highest high/lowest low during the trade lifecycle and shadows it `ATR * 2.0` away. 
 - **Exit Slippage Check:** Exiting a trade punishes the fill an additional `0.05%` natively: `real_exit = current_price * (1 +/- 0.0005)`.
- **Variables:** `slippage_bps`, `friction_factor`, `sl_dist`, `tp_dist`, `high_water_mark`, `low_water_mark`, `trailing_stop`, `pl`.

---

## 2. Data Feed, Mathematics & Market Geometry

### market_feed.py (Market Context Engine)
**What the code is actively doing:**
This file acts as the primary data ingestion engine. It connects to the Alpaca API (and falls back to `yfinance` if not in strict mode) to fetch high-resolution OHLCV (Open, High, Low, Close, Volume) data. It enhances raw price data by integrating tick-by-tick Cumulative Volume Delta (CVD) to measure buy/sell aggression, runs cross-exchange integrity checks to prevent stale data execution, and merges macro-economic indicators (DXY and US10Y) to gauge global liquidity. Finally, it acts as a translation layer, serializing the data into technical summaries and JSON payloads to be consumed by the AI agents.
- **Execution Flow:**
 - The primary entrypoint `get_live_market_data()` is called. It retrieves the appropriate symbol via `get_alpaca_symbol()` and fetches minute-bar market data through `get_alpaca_data()`.
 - If trading a stock and strict mode is active, it calculates real-time order flow using `calculate_cvd()`, adding `CVD` and `CVD_Grad` to the DataFrame.
 - A timestamp check is performed: if the last data point is older than `(tf_min * 60) + 900` seconds (during the workweek), the feed halts to prevent executing on stale data.
 - Technical indicators are appended via a call to `add_indicators()`.
- **Internal Functions:**
 - `get_macro_context()`: Fetches 5 days of DXY and TNX (^TNX) data to determine if the macro environment is 'STABLE' or 'VOLATILE'.
 - `get_alpaca_symbol(ticker)`: Converts Yahoo finance formats (e.g., EURUSD=X) into Alpaca standard symbols (e.g., EUR/USD).
 - `get_alpaca_data(ticker, period_days, strict)`: Connects to Alpaca's `StockHistoricalDataClient` to pull bars. Falls back to `yfinance` if official keys fail or forex data is requested, unless blocked by `strict` mode.
 - `calculate_cvd(symbol, start_date, end_date)`: Fetches raw tick trades. Applies the "Tick Rule" to approximate buy/sell sides, tallies the volume, calculates a cumulative sum, and resamples to match the OHLCV timeframe.
 - `audit_data_integrity(ticker, yahoo_price)`: Grabs the absolute latest trade from Alpaca using `StockLatestTradeRequest` and compares it to a Yahoo price. Fails if variance exceeds 0.15%.
 - `get_structured_context(ticker, period_days)`: Slices the last 100 dataframe rows, dropping nulls, and exports them to a JSON formatted string for AI context.
 - `generate_market_markdown(df, ticker)`: Extracts the final row of data and builds a markdown summary of price, SMA trend, and RSI.
 - `get_event_summary(df)`: Uses price logic and geometry imports to produce a list of "Technical Events" (SMA crossovers, RSI thresholds, FVG creation, Regime changes).
- **Mathematical Formulas:**
 - *Percentage Change (Macro)*: `((last_close / previous_close) - 1) * 100`
 - *Tick Rule Simulation*: `price_diff = price_t - price_{t-1}`. If `price_diff > 0`, `side = 1`. If `price_diff < 0`, `side = -1`.
 - *Order Flow Delta*: `delta = size * side`
 - *Integrity Deviation Threshold*: `abs(yahoo_price / alpaca_price - 1) * 100 > 0.15`
- **Variables:** `dxy`, `dxy_change`, `yield_change`, `api_key`, `secret_key`, `tf_min`, `strict`, `request_params`, `trades`, `cvd_resampled`, `alpaca_price`, `delay_seconds`, `allowable_delay`, `latest`, `events`, `regime_clf`.

### market_snapshot.py (Snapshot Generation)
**What the code is actively doing:**
This file generates a mission-critical, immutable "Source of Truth" snapshot for AI analysts. It pulls the raw feed, runs safety filters (e.g., avoiding sideways markets via Regime Filters), fetches Harvard Consensus Sentiment, and calculates structural math/geometry. Crucially, it enforces a "Zero-Cost Math Gate" which instantly kills the pipeline (`sys.exit(2)`) if the price is not near a Point of Interest (PoI)—saving expensive AI API calls. It strictly validates all outgoing numerical data using Pydantic schemas before dumping a final `market_snapshot.md` file.
- **Execution Flow:**
 - `create_market_snapshot()` invokes `get_live_market_data()` to acquire the core DataFrame.
 - Checks market regime via `check_market_regime()`. Aborts if trending momentum is non-existent.
 - Aggregates sentiment from `HarvardConsensusEngine`.
 - Calculates geometric support limits using `get_geometric_anchors`, `calculate_volume_profile`, and `calculate_volatility_floor`.
 - **Math Gate Check**: Measures the distance between current price and recent swing highs/lows. If the distance is greater than the ATR (Average True Range) threshold, and no immediate Fair Value Gaps or Liquidity Sweeps exist, it exits.
 - Packages the verified indicators into a dictionary and feeds it into the `MarketDataSchema` Pydantic model. If validation fails, throws a critical exception and terminates (`sys.exit(1)`).
 - Writes `snapshot_md` via atomic replacement to guarantee no race conditions while writing the file.
- **Internal Functions:**
 - `MarketDataSchema` (Class): Pydantic baseline defining strict greater-than/less-than limits (e.g., RSI must be between 0 and 100).
 - `check_non_zero(cls, v)`: A field validator assuring that prices, SMA, and channels are non-zero.
 - `create_market_snapshot(ticker)`: The orchestration pipeline tying data fetch, mathematical filtration, Pydantic validation, and disk I/O together.
- **Mathematical Formulas:**
 - *Proximity Threshold (Math Gate)*: `threshold = ATR` (or `last_close * 0.002` if ATR is unavailable).
 - *Geometric Distance Constraint*: `(dist_to_h < threshold)` or `(dist_to_l < threshold)`
- **Variables:** `df`, `sentinel`, `crowd`, `latest`, `geo_anchors`, `poc`, `va_low`, `va_high`, `vol_floor`, `last_close`, `atr`, `df_swings`, `last_high`, `last_low`, `dist_to_h`, `dist_to_l`, `threshold`, `has_fvg`, `is_near_level`, `avg_vol_15m`, `raw_payload`, `validated_data`.

### raw_data_processor.py (Numerical Tensor Compiler)
**What the code is actively doing:**
This file transforms and compresses standard OHLCV and L2 data into dense, high-resolution numeric tensors (comma-separated strings). Its explicit goal is to bypass the "Narrative Translation Tax" where LLMs lose mathematical precision due to bulleted English summaries. By generating raw CSV-like blocks representing micro-volatility, order flow absorption, and pair divergence, the AI models receive raw statistical reality.
- **Execution Flow:**
 - The `RawDataProcessor` class is instantiated with a window size.
 - Different pipeline requests (Macro, Micro 1H breakdown, Pair Divergence, or Compressed Tensors) route to their respective methods, mathematically mapping the raw pandas rows into normalized ratios.
 - Dataframes are strictly rounded and dumped into raw CSV strings without headers/indexes in order to minimize token usage.
- **Internal Functions:**
 - `prepare_macro_tensor(macro_dict)`: Formats simple global macro context strings.
 - `prepare_1h_micro_tensor(df_1h, df_15m)`: Iterates over the last four 1H candles, subdividing each into four 15m intervals to map the internal cumulative volume delta ratio (CVDR) and intra-candle volatility (IVOL).
 - `prepare_pair_tensor(df_a, df_b, beta)`: Aligns two assets, calculates their mathematical spread applying a beta weight, derives a Z-Score for statistical arbitrage, and returns a 30-period tensor string.
 - `calculate_wick_rejection_delta(df)`: Approximates Level 3 (Institutional) order book absorption. Evaluates the ratio between buying pressure in the lower wick and selling pressure in the upper wick, divided by candle body size.
 - `prepare_compressed_tensor(df)`: Normalizes the last 50 OHLCV rows to Close Percentages, Volume Ratios, RSI, and Acceleration. Returns a dense comma-delimited block representing the tensor map.
- **Mathematical Formulas:**
 - *Cumulative Volume Delta Ratio (CVDR)*: `Volume_Delta / Volume`
 - *Intra-Candle Volatility (IVOL)*: `(High - Low) / Open`
 - *Stat-Arb Spread*: `ln(Asset_A) - (Beta * ln(Asset_B))`
 - *Upper Wick Selling*: `High - max(Open, Close)`
 - *Lower Wick Buying*: `min(Open, Close) - Low`
 - *Wick Rejection Delta (L3 Sim)*: `(Lower_Wick - Upper_Wick) / abs(Close - Open)`
 - *Price Acceleration*: `second_derivative(Close_Percentage)` via `.diff().diff()`
 - *Volume Ratio*: `Volume / mean(Volume)`
- **Variables:** `dxy`, `tnx`, `recent_1h`, `h_start`, `h_end`, `sub_15m`, `cvdr`, `ivol`, `combined`, `log_a`, `log_b`, `spread`, `zscore`, `upper_wick`, `lower_wick`, `body_size`, `sim_delta`, `recent['CP']`, `recent['VR']`, `recent['PA']`.

### geometry.py (The Structural Market Pattern Engine)
**What the code is actively doing:**
This file identifies spatial, institutional-grade market geometry directly mathematically, mapping concepts popularized by Smart Money Concepts (SMC) and Inner Circle Trader (ICT). It functionally calculates swing pivots, Fair Value Gaps (FVG), inter-market divergence, volume profiles, and liquidity sweeps while strictly mitigating lookahead bias. 
- **Execution Flow:**
 - DataFrames are routed through isolated mathematical functions.
 - Calculations rely on trailing windows and index offsets to guarantee that structural shapes (like Swing Highs) are only acknowledged *after* they are historically confirmed.
 - The orchestrator function `get_geometric_anchors` aggregates all these independent signals into a cohesive mathematical map to ground vision/language agents.
- **Internal Functions:**
 - `calculate_swing_points(df, window)`: Looks for maximums/minimums over a `2*window+1` rolling period, but shifts the result back by `window` to establish the historical swing pivot without lookahead bias.
 - `calculate_fvg(df)`: Checks consecutive 3-candle arrays for imbalances where `Low[i] > High[i-2]` (Bullish) or `High[i] < Low[i-2]` (Bearish). 
 - `calculate_smt_divergence(df_primary, df_correlated)`: Identifies if a primary asset fails to make a higher high/lower low while a correlated asset succeeds, flagging "SMT Divergence".
 - `calculate_volume_delta(df)`: Simulates buying vs selling pressure mathematically by mapping intra-bar wick distances against volume.
 - `detect_liquidity_sweeps(df)`: Monitors if the current candle temporarily penetrates a verified past swing point but reverses to close back inside the previous range ("Stop Runs/Springs").
 - `check_geometric_distance(point_a, point_b)`: Calculates the simple Euclidean distance.
 - `calculate_volatility_floor(df)`: Computes a rolling standard deviation to determine a "Noise Floor" threshold in absolute price to prevent HFT stop-hunting.
 - `calculate_volume_profile(df, bins)`: Segments closing typical prices into bins. Sums the volume per bin, identifying the maximum as the Point of Control (POC) and deriving the 70% bounds as the Value Area.
 - `detect_absorption(df)`: Flags price action where mathematically normalized volume delta deviates >2 Sigma, but the candle body size is abnormally small (implying institutional limit blocking).
 - `get_geometric_anchors(df)`: Collates FVGs, sweeps, absorption signals, volume profiles, and proximity measurements into a unified summary block.
- **Mathematical Formulas:**
 - *Swing Confirmation Index*: `Current_Index - Window`
 - *Buying Pressure Proxy*: `(Close - Low) / (High - Low)`
 - *Selling Pressure Proxy*: `(High - Close) / (High - Low)`
 - *Volatility Floor Offset*: `Price * stdev(pct_change(Close), window)`
 - *Typical Price (Volume Profile Bin)*: `(High + Low + Close) / 3`
- **Variables:** `high_indices`, `low_indices`, `fvg_zones`, `p_lows`, `c_lows`, `range_val`, `buy_pressure`, `sell_pressure`, `delta`, `sweeps`, `prev_high`, `prev_low`, `std_dev`, `price_bins`, `vprofile`, `poc_bin`, `va_low`, `va_high`, `is_high_delta`, `is_small_body`.

### indicators.py (The Pure Mathematics Library)
**What the code is actively doing:**
This file implements standard Technical Analysis (TA) calculations using pure `pandas` and `numpy`. It deliberately avoids external libraries (like `TA-Lib`) to ensure full transparency and exact matching with Wilder's standard smoothing algorithms found on MT4 or TradingView.
- **Execution Flow:**
 - Contains purely functional mathematical transformations. Each function takes a pandas Series or DataFrame and returns the calculated technical values.
 - `add_indicators()` operates as a centralized macro function, taking raw OHLCV and appending all standard technical markers directly as columns onto the source DataFrame.
- **Internal Functions:**
 - `calculate_rsi(series, period)`: Implements Wilder's Smoothed Moving Average (SMMA) RSI, mapping momentum based on prior gains vs losses.
 - `calculate_sma` / `calculate_ema`: Standard pandas `.rolling().mean()` and `.ewm(span).mean()` functions.
 - `calculate_atr(df, period)`: Calculates True Range (maximum daily volatility gap), applying Wilder's smoothing.
 - `calculate_adx(df, period)`: Computes Positive and Negative Directional Movement (+DM, -DM), smooths them, normalizes against ATR to generate +DI/-DI, and smooths the variance to find the ADX trend strength.
 - `calculate_donchian(df, period)`: Finds rolling local minimum and maximum to form dynamic support/resistance channels.
 - `calculate_pivots(df)`: Derives Standard Pivot Points (P, Support 1, Resistance 1) based on the prior candle's High, Low, and Close.
 - `calculate_zscore(series, window)`: Calculates the standard deviation normalized spread from the rolling mean.
 - `calculate_beta(asset_returns, market_returns, window)`: Derives correlation strength against a baseline benchmark using standard covariance math.
 - `calculate_ou_params(series)`: Uses a Scipy linear regression to fit a time series into an Ornstein-Uhlenbeck (mean-reverting) process, solving for the speed of reversion and the half-life.
 - `add_indicators(df)`: Appends `RSI_14`, `ATR_14`, `ADX_14`, `SMA_20`, `EMA_20`, `DCL_20`, `DCU_20`, and `Pivot` data directly onto the input dataframe.
- **Mathematical Formulas:**
 - *Wilder’s Smoothing Function*: `current_avg = (prev_avg * (period - 1) + current_val) / period`
 - *True Range (TR)*: `max((High - Low), abs(High - PrevClose), abs(Low - PrevClose))`
 - *RSI Relative Strength (RS)*: `Average_Gain / Average_Loss`
 - *RSI Base*: `100 - (100 / (1 + RS))`
 - *Pivot Point (P)*: `(Prior_High + Prior_Low + Prior_Close) / 3`
 - *Resistance 1 (R1)*: `(2 * P) - Prior_Low`
 - *Support 1 (S1)*: `(2 * P) - Prior_High`
 - *Beta*: `Covariance(Asset, Market) / Variance(Market)`
 - *OU Reversion Speed (Lambda)*: `-ln(Slope_Beta)` (Where beta is derived from regressing current values against lag-1 values)
 - *OU Half-Life*: `ln(2) / Lambda`
- **Variables:** `delta`, `gain`, `loss`, `avg_gain`, `avg_loss`, `tr1`, `tr2`, `tr3`, `up_move`, `down_move`, `plus_dm`, `minus_dm`, `smooth_plus_dm`, `plus_di`, `minus_di`, `dx`, `adx`, `upper`, `lower`, `cov`, `var`, `s_t`, `s_prev`, `beta`, `alpha`, `lmbda`, `half_life`, `mu`.

### pro_data_bridge.py (Polygon API Bridge)
**What the code is actively doing:**
This acts as a professional-grade adapter for the Polygon.io API. It replaces the unstable Yahoo Finance ('Toy Data') baseline for high-fidelity macro-level or benchmark assets with institutional-grade aggregated 1-hour bar data. 
- **Execution Flow:**
 - The `ProDataBridge` instance sets up authentication headers utilizing the `POLYGON_API_KEY`.
 - When `get_macro_data()` is requested, it calculates dynamic start and end dates relative to the execution timestamp.
 - It shapes a valid Polygon.io API request URL utilizing string translations for standard assets.
 - A network request is dispatched. The resulting milliseconds epoch timestamps are converted into pandas datetime structures for standard ingestion.
- **Internal Functions:**
 - `__init__()`: Loads environmental variables and anchors the Polygon base URL.
 - `get_macro_data(ticker, days)`: Translates simple ticker names to Polygon's internal notation (e.g., prefixing `C:` for forex). Queries the REST API for a defined rolling window of days. Standardizes column names (`o`, `h`, `l`, `c`, `v` mapping to `Open`, `High`, etc.) and sets the index to the Timestamp.
- **Mathematical Formulas:**
 - *Date Range Trailing*: `start = Current_Date - timedelta(days)`
 - *Time Normalization*: Milliseconds from Unix Epoch `(df['t'])` converted via `unit='ms'`.
- **Variables:** `api_key`, `base_url`, `poly_ticker`, `end`, `start`, `url`, `res`, `data`, `df`.

### price_watch.py (OANDA Price Watchdog)
**What the code is actively doing:**
This file operates as an autonomous, high-frequency "Watchdog" risk manager. It runs an infinite loop that connects directly to OANDA’s pricing WebSockets. It constantly monitors active orders within `trade_journal.json`, and if the real-time mid-price of an asset breaches a predetermined Stop Loss (SL), it immediately fires a market-close REST request to OANDA, overriding normal delayed evaluation intervals.
- **Execution Flow:**
 - Loads credentials and initializes an instance of `oandapyV20.API` targeting the "practice" environment.
 - `stream_and_monitor()` opens a perpetual `while True:` loop.
 - Parses `trade_journal.json` to find any dictionary entries with `status == "OPEN"`.
 - Dynamically builds a list of active instrument strings formatted for OANDA.
 - Establishes a `PricingStream` WebSocket connection to OANDA.
 - Consumes the tick stream sequentially. Averages the bid/ask to find the `mid_price`.
 - Validates the real-time mid-price against the target SL. If breached, the Watchdog executes `close_trade()` synchronously, intercepts the `trade_id`, and mutates the JSON database to log the outcome as closed, updating precise Profit/Loss (PnL) metrics, and breaking the inner loop to reload active positions. 
- **Internal Functions:**
 - `__init__()`: Environmental credential bootstrapping.
 - `close_trade(trade_id)`: Issues an imperative `TradeClose` order block to OANDA. Returns True if the request resolved cleanly.
 - `stream_and_monitor()`: Handles file I/O for state tracking, builds WebSocket stream filters, executes tick-by-tick comparative loops, handles failure/reconnection logic with `time.sleep()`, and runs SL breach calculations.
- **Mathematical Formulas:**
 - *Mid-Price Calculation*: `(Bid_Price + Ask_Price) / 2`
 - *Long PnL*: `(Exit_Price - Entry_Price) * Quantity`
 - *Short PnL*: `(Entry_Price - Exit_Price) * Quantity`
 - *Long Exit Trigger*: `RealTime_Price <= SL`
 - *Short Exit Trigger*: `RealTime_Price >= SL`
- **Variables:** `access_token`, `account_id`, `client`, `journal`, `active_trades`, `instruments`, `params`, `r`, `tick`, `instrument`, `price`, `sl`, `direction`, `trade_id`, `entry_price`, `qty`, `trigger_exit`, `pl`.

---

## 3. Sentiment & Global Macro Sentinels

### sentiment_sentinel.py (Harvard Consensus Engine)
**What the code is actively doing:**
- **Execution Flow**: When instantiated, the `HarvardConsensusEngine` sets up connections to Alpaca's Historical News API, live WebSocket streams, and initializes a Google Gemini LLM (`gemini-1.5-flash`). The core orchestrator is `run_sentinel()`. When called for a specific ticker, it gathers data from multiple distinct sources: retail trader positioning via the DailyFX API and recent news headlines via Alpaca. These sources are treated as independent "votes". The engine applies a contrarian logic to retail positions and uses Gemini to assign a numeric sentiment score to the news. It then calculates a weighted, trimmed mean of these votes. The system adjusts its own confidence score based on how many APIs are successfully online. The final computed sentiment thesis is saved to a local JSON file (`last_valid_bias.json`) for the rest of the bot to consume. The class also supports persistent real-time streaming via `start_live_ingestion()`, which listens for live news over WebSockets. When a headline drops, `_on_news()` instantly evaluates it via the LLM and completely overrides the system's current sentiment bias.
- **Internal Functions**:
 - `_on_news()`: Callback for the live WebSocket. Immediately passes a breaking headline to Gemini and triggers `run_sentinel()` with a high-priority override.
 - `start_live_ingestion()`: Connects to Alpaca's news WebSocket and enters a blocking loop (`_run_forever`).
 - `_fetch_alpaca_news()`: Queries Alpaca's REST API for headlines from the last 2 hours, capped at 10 results.
 - `_fetch_retail_ratios()`: Pings DailyFX to extract retail long vs. short percentages. 
 - `validate_bias()`: A schema validator that ensures LLM outputs are castable to a float and clamped between -1.0 and 1.0.
 - `analyze_anonymous_votes()`: Processes raw API data into "votes". Converts extreme retail positions into a contrarian bias and sends batched news to Gemini for scoring.
 - `calculate_trimmed_mean()`: Performs a weighted average of the computed votes.
 - `run_sentinel()`: Main orchestrator that fetches, aggregates, calculates confidence, and determines "herd status".
 - `_save_state()`: Safely persists the final dictionary to disk using a temporary file and atomic replace.
- **Mathematical Formulas used**:
 - **Contrarian Retail Bias**: If `Retail Long % > 0.70`, bias is assigned `-1.0` (Sell). If `Retail Short % > 0.70`, bias is assigned `+1.0` (Buy).
 - **Trimmed Mean Weighted Average**: $Final Bias = \frac{\sum (Bias \times Weight)}{\sum Weight}$. Retail data has a weight of `1.0`, Historical Gemini News has a weight of `1.2`, and Live WebSocket News overrides with a weight of `1.5`.
 - **Confidence Score**: Drops exponentially if data sources fail. `0.90` for $\ge 2$ sources, `0.50` for $1$ source, `0.10` for $0$ sources. If $0$ sources are online, the final bias is neutralized to $0.0$.
- **Variables**: `api_key`/`secret_key` (Alpaca credentials), `junior_cfg` (LLM temperature and model config), `current_ticker` (asset symbol), `retail` (long/short percentages), `news` (list of strings), `confidence_score` (reliability metric), `aggregated_bias` (final numeric sentiment), `herd_status` (string categorical marker like "EXTREME_RETAIL_BULLISH").

### news_sentinel.py (Fundamental Catalyst & Divergence Detector)
**What the code is actively doing:**
- **Execution Flow**: This module evaluates news *relevance* and detects market *divergences*, simulating a real-time news wire. When `audit_news_relevance()` is called, it simulates the age of incoming news and strictly filters out headlines that are either too fresh (assuming High-Frequency Trading bots have already front-run the liquidity) or too old (stale). It targets a specific "Retail Sentiment" window. When `get_sentiment_divergence()` is called, it assigns a rudimentary keyword-based sentiment score to headlines and cross-references it with a provided 7-day price change to identify "Information Asymmetry" (e.g., highly bullish news, but the price is dropping heavily, indicating a leading divergence).
- **Internal Functions**:
 - `get_latest_headlines()`: Currently a placeholder that returns mocked news strings. Intended to wrap a financial RSS or API.
 - `audit_news_relevance()`: Generates a random simulated age for the news (in minutes) and rejects it if it falls outside the acceptable timeframe.
 - `get_sentiment_divergence()`: Performs basic NLP word-matching against the headlines to determine a score, and flags Bullish or Bearish divergences based on the opposite price action.
- **Mathematical Formulas used**:
 - **Keyword Sentiment Score**: `+0.2` for every bullish keyword ("bullish", "buy", "growth", "earnings beat", "upgrade"). `-0.2` for every bearish keyword ("bearish", "sell", "investigation", "miss", "downgrade"). Score is bounded to $[-1.0, 1.0]$.
 - **Bullish Divergence Logic**: Triggers if `sentiment_score > 0.3` AND `price_change_7d < -2.0%`.
 - **Bearish Divergence Logic**: Triggers if `sentiment_score < -0.3` AND `price_change_7d > 2.0%`.
 - **News Window Constraints**: Rejects if $Age < 5 \text{ mins}$ or $Age > 1440 \text{ mins}$ (24 hours).
- **Variables**: `headlines` (array of text), `sim_age_mins` (mocked timestamp age), `min_age`/`max_age` (configurable time boundaries), `bullish_words`/`bearish_words` (static dictionary arrays), `sentiment_score` (calculated float), `divergence` (categorical output string).

### global_sentinel.py (Global Macro Veto Engine)
**What the code is actively doing:**
- **Execution Flow**: This module acts as the ultimate macro-environment failsafe. It pulls price data for major "Lead" global assets (like DXY, VIX, US10Y). It relies on a `ProDataBridge` instance to pull hourly institutional data from Polygon.io, with an automatic failover to the free `yfinance` library if the primary API fails. Once the price data over the last 2 days is collected, it calculates the 5-hour rate of change (RoC) for these macro indicators. `check_global_veto()` evaluates these RoCs against hardcoded thresholds. If the broader market conditions are hostile to the requested trade direction (e.g., trying to long Gold during a massive Yield spike or long Euros during a parabolic Dollar run), it issues a "VETO", blocking the trade.
- **Internal Functions**:
 - `get_macro_weather()`: Iterates through macro tickers, fetches recent hourly price data, and calculates the 5-hour percentage change.
 - `check_global_veto()`: Main logic gate. Reads the macro weather and applies three specific veto rules (Risk-Off, Dollar Strength, Yield Spike) to the proposed trade.
- **Mathematical Formulas used**:
 - **5-Hour Rate of Change (RoC)**: $(Latest Close - Close_{t-5}) / Close_{t-5}$.
 - **VIX Risk-Off Veto**: `VIX Price > 30` AND `direction == "LONG"`.
 - **DXY Parabolic Veto**: `DXY 5h_change > 0.005` (0.5%) AND Ticker opposes USD (EURUSD, GBPUSD, AUDUSD) AND `direction == "LONG"`.
 - **Yield Spike Veto**: `US10Y 5h_change > 0.02` (2.0%) AND Ticker is interest-sensitive (XAUUSD, NQ) AND `direction == "LONG"`.
- **Variables**: `leads` (list of macro assets to monitor), `df` (pandas DataFrame containing time-series data), `weather` (dictionary mapping asset to latest price and RoC), `dxy_move`, `vix_price`, `yield_move` (extracted macro states), `is_against_usd` (boolean flag).

### connectivity_sentinel.py (Latency & Jitter Monitor)
**What the code is actively doing:**
- **Execution Flow**: Essential for local/home-server high-frequency setups, this module monitors ISP health. When `is_safe_to_trade()` is called, the class subprocesses a command-line Ping operation to the target broker's API server (default Alpaca). It parses the raw command-line text output to extract the average latency in milliseconds. If the latency exceeds a predefined jitter threshold, it flags the network as unsafe, preventing the bot from submitting trades into a slow or disconnecting environment.
- **Internal Functions**:
 - `check_latency()`: Determines OS (Windows vs Mac/Linux), executes the proper ping command via `subprocess`, parses the string output, and returns the float latency in ms. Returns `999` upon failure as a safety net.
 - `is_safe_to_trade()`: Evaluates the latency against the defined class limits.
- **Mathematical Formulas used**:
 - **Jitter Block**: Returns `False` if $Latency > 350 \text{ ms}$.
- **Variables**: `target_host` (API endpoint URL), `max_ping_ms` (integer threshold of 350), `max_packet_loss` (float limit of 0.05), `command` (array of OS arguments), `output` (raw string from console), `latency` (parsed milliseconds as float).

### pro_sentiment_engine.py (Institutional Polygon News Engine)
**What the code is actively doing:**
- **Execution Flow**: This is a direct pipeline to Polygon.io's reference news API, bypassing web scrapers for institutional-grade reliability. It constructs an HTTP GET request to Polygon using the asset ticker, fetches up to 10 recent news objects, and extracts the titles. Because a local LLM is temporarily unhooked in this file, it relies on a proxy logic where the pure *volume/count* of news articles fetched is mapped to an "urgency score", acting as a stand-in for sentiment intensity.
- **Internal Functions**:
 - `get_asset_sentiment()`: Formats the ticker (removing dashes or equals signs), builds the request parameters, handles the REST API call, and parses out the "title" fields from the JSON payload.
- **Mathematical Formulas used**:
 - **Urgency Score**: $Number\ of\ Headlines\ Fetched / 10.0$.
- **Variables**: `api_key` (Polygon auth), `base_url` (v2/reference/news endpoint), `clean_ticker` (sanitized symbol string), `params` (API query arguments), `news` (JSON array of article objects), `headlines` (list of string titles), `urgency_score` (calculated float).

### cheap_sentiment_scraper.py (Zero-Cost Local AI Scraper)
**What the code is actively doing:**
- **Execution Flow**: This module operates as a cost-saving alternative to paid NLP APIs. It first attempts to grab news using the existing Alpaca API integration via `sentiment_sentinel.py`. If Alpaca returns nothing or fails, it initiates a fallback Web Scraper. It sends an HTTP request masquerading as a web browser to ForexFactory, uses BeautifulSoup to parse the HTML DOM, and rips text from specific div classes (`flex-1`). Once headlines are gathered from either source, it constructs a prompt containing the top 15 headlines and sends them to a locally hosted LLM (Llama 3.1) via `LocalLLMClient`. The local LLM calculates the sentiment bias, keeping API costs at strictly $0.
- **Internal Functions**:
 - `scrape_headlines()`: Executes an HTTP GET request with a spoofed User-Agent. Parses the response with BeautifulSoup to find and extract the text from the top 10 news items.
 - `get_market_bias()`: The main pipeline. Attempts Alpaca API first, triggers `scrape_headlines()` on fail. Formats the retrieved text into an LLM prompt, invokes the local model, parses the string float return, and categorizes the bias.
- **Mathematical Formulas used**:
 - **Categorical Bias Assignment**: 
  - `BULLISH` if $bias\_score > 0.3$.
  - `BEARISH` if $bias\_score < -0.3$.
  - `NEUTRAL` if between $[-0.3, 0.3]$.
- **Variables**: `sources` (dictionary of target URLs), `local_ai` (instance of `LocalLLMClient`), `headers` (spoofed browser info), `soup` (BeautifulSoup HTML object), `items` (HTML DOM nodes), `headlines` (array of text), `prompt` (string sent to Llama), `bias_score` (parsed float), `status` (string label).

---

## 4. Trading Strategies, Allocators & Classifiers

### pairs_trading_scanner.py (Statistical Arbitrage Engine)
**What the code is actively doing:**
This file implements a sophisticated pairs trading algorithm (`CorrelationArbitrageEngine`) that trades the mean reversion of the spread between two historically correlated assets.
- **Execution Flow**: When invoked to scan, it prioritizes "Index-Basis" pairs (e.g., an individual stock against its sector ETF, like NVDA vs SOXX) from a hardcoded `BASIS_MAP`. It fetches the last 60 days of market data for both assets. If the return correlation exceeds 0.90, it calculates the spread's Z-score. If the absolute Z-score surpasses the configured `z_threshold` (default 3.0), the pair is flagged as an anomaly ready for arbitrage. If no basis pairs trigger, it runs a standard cross-pair scanner (`_find_best_standard_pair`) testing all combinations of given tickers (checking for correlation > 0.85) to find the pair with the maximum divergence.
- **Internal Functions**:
 - `__init__(self)`: Initializes the engine with a 60-day lookback window and fetches `z_threshold` from `config_loader`.
 - `get_spread_zscore(self, asset_a_df, asset_b_df)`: The core math engine. Aligns the data, calculates beta, generates the spread, and normalizes it to a Z-score.
 - `find_best_index_basis_pair(self, tickers)`: Filters through the hardcoded `BASIS_MAP` to find the most diverged ETF/Stock pair.
 - `find_best_pair(self, tickers)`: Orchestrator that tries the basis map first, then falls back to standard pairs.
 - `_find_best_standard_pair(self, tickers)`: Brute-force correlation scanner across all $N \times (N-1)/2$ combinations of provided active tickers.
- **Mathematical Formulas**:
 - **Log Transformation**: $log\_a = \ln(AssetA\_Close)$, $log\_b = \ln(AssetB\_Close)$
 - **Dynamic Spread**: $Spread = \ln(A) - (\beta \times \ln(B))$ (Creates a Beta-Neutral spread calculation)
 - **Z-Score Normalization**: $Z = \frac{Spread - \mu_{Spread}}{\sigma_{Spread}}$ (calculated over the 60-day lookback window via `calculate_zscore`)
- **Variables**:
 - `lookback` (60): Rolling window length for statistical calculations.
 - `z_threshold` (3.0): Minimum standard deviations away from the mean required to trigger a trade.
 - `BASIS_MAP`: Hardcoded dictionary mapping specific assets to their index/ETF anchor (e.g., "GOLD" -> "GDX").

### fundamental_divergence.py (Fundamental Divergence & Liquidity Guard)
**What the code is actively doing:**
This file operates as an advanced "Terminal Alpha" divergence scanner, primarily focusing on dual-listed assets or ADRs against their primary indices ("Quiet Niche"). It aims to detect structural mispricings while protecting against negative carry costs and liquidity traps.
- **Execution Flow**: The `FundamentalDivergence` class is initialized with a primary ticker (e.g., "GOLD") and an anchor ticker ("GDX"), pulling mapped FX and rate proxies from `NICHE_MAP`. When `analyze()` is called, it fetches recent price, volume, and macroeconomic data (local rates vs. US rates). It calculates the direct price ratio of the primary asset to its anchor and its historical Z-score. Before returning a trade signal, it checks two major veto conditions: a "Carry Veto" (if holding the asset costs too much in yield difference) and a "Liquidity Veto" (if the relative volume is suspiciously low during the divergence).
- **Internal Functions**:
 - `__init__(self, primary_ticker, anchor_ticker)`: Sets up tickers and macro indicators (FX, rate proxy).
 - `analyze(self, lookback_days)`: Fetches data via Alpaca and yfinance APIs, calculates mathematical ratios, applies vetos, and returns a detailed divergence report dictionary.
- **Mathematical Formulas**:
 - **Asset Ratio**: $Ratio = \frac{Primary\_Close}{Anchor\_Close}$
 - **Carry Risk / Leakage**: $Carry\_Risk = Local\_Rate - US\_Rate (\text{^TNX})$ (Yield spread)
 - **Volume Z-Score**: $Vol\_Z = \frac{Volume_{current} - SMA(Volume, 20)}{StdDev(Volume, 20)}$
 - **Divergence Z-Score**: $Z = \frac{Ratio_{current} - \mu_{Ratio}}{\sigma_{Ratio}}$
- **Variables**:
 - `NICHE_MAP`: Configuration mapping for niche assets (e.g., BHP to PICK, tracking USDAUD=X and ^TNX).
 - `signal`: Output string resolving to "NEUTRAL", "LIQUIDITY_VETO", "CARRY_VETO", or "QUIET_ALPHA_CANDIDATE".

### contrarian_module.py (Contrarian Trap Hunter)
**What the code is actively doing:**
This module is designed to fade retail traders. It looks for typical "Smart Money Concept" (SMC) signals that trap retail investors, triggering a counter-trade when institutional absorption is detected instead.
- **Execution Flow**: When historical data is passed to `identify_trap_scenarios()`, it calls external geometric analysis functions (`detect_liquidity_sweeps`, `detect_absorption`) to scan for opposing market forces. It cross-references retail signals (sweeps) against institutional actions (absorption). If a retail bearish sweep is met with bullish institutional absorption, it flags a "TRAP_THE_BEARS" scenario. Conversely, a retail bullish sweep met with bearish absorption triggers a "TRAP_THE_BULLS" scenario.
- **Internal Functions**:
 - `identify_trap_scenarios(self, df)`: The core logic function. Correlates sweep and absorption events to return a list of actionable traps with detailed rationale.
- **Mathematical Formulas**:
 - It relies on boolean/set intersection logic applied to the outputs of geometric modules: $Trap_{Bear} = Bearish\_Sweep \cap Bullish\_Absorption$.
- **Variables**:
 - `bear_sweeps`, `bull_abs`, `bull_sweeps`, `bear_abs`: Filtered lists containing dictionary structures of geometric market events.
 - `retail_bias` / `institutional_intent`: Directional strings ("LONG" or "SHORT") assigning motives to the market participants.

### allocator.py (Hedged Position Sizer)
**What the code is actively doing:**
This file handles risk management and position sizing specifically for Beta-Neutral paired arbitrage. It ensures that any given pair trade has balanced notional exposure to neutralize directional market movement risks.
- **Execution Flow**: `get_borrow_fee_veto` is first evaluated to check if the asset is "Hard-To-Borrow" (HTB), halting execution if shorting the asset is too expensive (exceeds a 5% APR fee limit). `get_hedged_quantities` then calculates the exact number of shares needed for Asset A based on the inputted dollar risk. It scales the necessary counter-position quantity for Asset B by factoring in the calculated Beta to maintain market neutrality.
- **Internal Functions**:
 - `get_borrow_fee_veto(ticker, side)`: A static method simulating a check against broker borrow fees. Vetoes the trade (returns False) if the estimated fee > max fee.
 - `get_hedged_quantities(risk_usd, price_a, price_b, beta, direction_a)`: A static method generating the exact quantity and side (LONG/SHORT) for both legs of the pair trade.
- **Mathematical Formulas**:
 - **Asset A Quantity**: $Qty_A = \frac{\max(Risk\_USD, 5.0)}{Price_A}$
 - **Beta-Hedged Notional B**: $Notional_B = (Qty_A \times Price_A) \times |\beta|$
 - **Asset B Quantity**: $Qty_B = \frac{Notional_B}{Price_B}$
- **Variables**:
 - `max_fee` (5.0): Maximum allowable borrow APR for short positions.
 - `side_a` / `side_b`: String literal ("LONG" or "SHORT") strictly inverted between assets.

### regime_classifier.py (Market Regime Classifier)
**What the code is actively doing:**
This script evaluates current market dynamics to categorize the overarching "Personality" or "Regime" of the market. This categorization prevents the core bot from blindly applying trend-following strategies in choppy markets or mean-reverting strategies during aggressive, parabolic trends.
- **Execution Flow**: `classify()` takes a dataframe and reads the latest ADX (Average Directional Index) and ATR (Average True Range). It first calculates an `ATR_Ratio` to check for abnormal volatility spikes. If the ratio > 3.0, it triggers an emergency "PARABOLIC_CHAOS" veto to halt all trading. Otherwise, it uses ADX to determine if there's a strong trend (> 30). If trending, it compares the price to a 20-period SMA to output Bull/Bear Momentum or Controlled Drift. If not trending (ADX <= 30), it uses the ATR ratio to output Volatile Chop or Quiet Range.
- **Internal Functions**:
 - `classify(self, df)`: Processes the latest row of data through nested conditional logic blocks to output a defined market regime and its functional description.
- **Mathematical Formulas**:
 - **Volatility Spike Ratio**: $ATR\_Ratio = \frac{ATR_{14\_Current}}{\mu(ATR_{14} \text{ over last 50 periods})}$
 - **Directional Alignment**: $Price\_vs\_SMA = \frac{Close - SMA_{20}}{SMA_{20}}$
- **Variables**:
 - `REGIMES`: Dictionary defining the 6 possible market states and their qualitative descriptions.
 - `adx`: Scalar float dictating trend strength presence (threshold is 30).

### strategy_library.py (Alpha Strategy Router)
**What the code is actively doing:**
This file acts as a centralized repository and unified router for different trading strategies. It provides a standard interface (`get_signal`) for the core execution engine to poll multiple algorithmic approaches.
- **Execution Flow**: It defines a base `AlphaStrategy` class and three specific concrete implementations (`ContrarianHunter`, `StatArbSpecialist`, `TrendFollower`). When `get_signal()` is called on an instance, it instantiates the corresponding functional logic class from the other files (e.g., `ContrarianTrapHunter`, `PairsScanner`), feeds it the current market dataframe, and translates the output into a standardized dictionary containing the "direction" and "confidence" score.
- **Internal Functions**:
 - `AlphaStrategy.__init__(self, name)`: Base class constructor.
 - `ContrarianHunter.get_signal(self, df)`: Instantiates `ContrarianTrapHunter`. Returns the institutional intent direction with an arbitrary 0.8 confidence if a trap exists.
 - `StatArbSpecialist.get_signal(self, df, pair_df)`: Calculates the pair's Z-score. Triggers at a Z-score of > 2.0 (SHORT_SPREAD) or < -2.0 (LONG_SPREAD) with 0.75 confidence.
 - `TrendFollower.get_signal(self, df)`: A standalone momentum algorithm returning momentum direction based on ADX and EMA with 0.6 confidence.
- **Mathematical Formulas**:
 - **Trend Follower Logic**: Triggers if $ADX_{14} > 25$. If true, checks if $Close > EMA_{20}$ (LONG) or $Close < EMA_{20}$ (SHORT).
- **Variables**:
 - `STRATEGY_MAP`: A mapping dictionary holding instantiated strategy objects, allowing string-based lookup for active routing ("CONTRARIAN_TRAP", "STAT_ARB", "TREND_FOLLOW").
 - `confidence`: Hardcoded float values estimating the win probability or weighting priority of each strategy's signal.

---

## 5. State Management, Reconciliation & Self-Learning

### database_manager.py (Trade State & System Database Management)
**What the code is actively doing:**
This file acts as the primary data persistence layer for the trading bot by utilizing an ACID-compliant SQLite database. It eliminates the corruption and synchronization risks associated with flat JSON files, replacing them with structured and transactional database commands. 
- **Execution Flow & Internal Functions:**
 - `__init__(self, db_path="trading_state.db")`: Initializes the database by executing `_init_db()`.
 - `_init_db(self)`: Uses `sqlite3` to establish a connection to `trading_state.db`. It explicitly creates two SQL tables if they do not exist: `trades` and `system_state`.
 - `add_trade(self, trade_data)`: Takes a dictionary (`trade_data`), extracts variables like `asset`, `direction`, `confidence_level`, and `full_decision`, then performs an `INSERT` statement into the `trades` table. The `status` is hardcoded to "OPEN" and the timestamp is dynamically generated as UTC. It returns the `lastrowid`.
 - `update_trade(self, ticker, direction, update_dict)`: Modifies an existing open trade. It takes a dictionary of properties to update and formats an `UPDATE trades SET {keys} = ? WHERE asset = ? AND direction = ? AND status = 'OPEN' ORDER BY id DESC LIMIT 1`. This safely ensures only the most recent open trade for a specific ticker/direction is altered.
 - `get_open_trades(self)`: Executes `SELECT * FROM trades WHERE status = 'OPEN'` and returns the fetched rows as a list of dictionaries via `sqlite3.Row` factory.
 - `get_recent_history(self, ticker, limit=5)`: Executes a `SELECT *` query bounded by the asset ticker, ordering by `id DESC` to pull the most recent trades for analysis up to the specified `limit`.
 - `set_state(self, key, value)` & `get_state(self, key, default=None)`: Allows the bot to write and read global system configurations using the `system_state` key-value table. `set_state` uses `INSERT OR REPLACE INTO` for seamless upserting.
- **Variables & Data Types:** `trade_data`, `update_dict`, `db_path`.

### account_reconciler.py (Broker-to-Database Synchronization)
**What the code is actively doing:**
This file acts as an auditing mechanism to ensure the local SQLite database's understanding of open trades exactly matches the actual open positions registered in the Alpaca broker API. It strictly prevents "Double Exposure" (buying an asset twice) and "Trade Amnesia" (losing track of an active trade).
- **Execution Flow & Internal Functions:**
 - `__init__(self)`: Instantiates the Alpaca `TradingClient` using environmental variables (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`) set to paper trading mode, and connects to the local `TradingDatabase`.
 - `reconcile_positions(self)`: 
  - **Step 1:** Polls the Alpaca API via `self.client.get_all_positions()` to fetch the absolute truth of active market positions.
  - **Step 2:** Calls `self.db.get_open_trades()` to retrieve the local database's belief of what should be open.
  - **Step 3 (Ghost Trade Audit):** Iterates over local database trades. It performs string manipulation to align asset tickers (e.g., transforming a database ticker `"EUR-USD=X"` to Alpaca's expected `"EUR/USD"`). If a local open trade is *not* found in the active Alpaca positions list, the local system flags it as a "Ghost Trade" and defensively updates the SQLite database record to `status = "CLOSED"` with the `exit_reason = "RECONCILIATION_SYNC"`.
  - **Step 4 (Unrecorded Position Audit):** Iterates through active Alpaca positions. If it spots a position running in the broker that is unrecorded locally, it logs a warning but deliberately does not insert it into the database to avoid infinite logic loops.
- **Variables & Data Types:** `broker_assets`, `db_asset`, `base`, `quote`.

### atomic_ops.py (Concurrency & Race-Condition Prevention)
**What the code is actively doing:**
This file establishes safe, cross-platform I/O operations for interacting with JSON files across multiple threads or processes. It employs a temporary `.lock` file protocol and intermediate `.tmp` files to guarantee that data isn't corrupted mid-write.
- **Execution Flow & Internal Functions:**
 - `FileLock` Class: 
  - `acquire(self, timeout=10)`: Implements a spin-lock waiting loop (`while os.path.exists(self.lock_file): time.sleep(0.1)`). If the `timeout` is exceeded, it forcefully breaks the loop. When free, it creates the lock file and writes the current Process ID (`os.getpid()`).
  - `release(self)`: Deletes the lock file if it exists.
 - `atomic_write_json(file_path, data)`: Instantiates a `FileLock`. Once acquired, it serializes the JSON `data` into a temporary file (`file_path + ".tmp"`). Only after the write completely finishes does it perform `os.replace(temp_path, file_path)`, which provides an atomic OS-level file swap. Finally, it releases the lock via a `finally` block.
 - `atomic_read_json(file_path, default=None)`: Employs the identical locking mechanism to ensure the file isn't read while another process is halfway through rewriting it. If a read failure occurs, it gracefully returns a `default` fallback payload.
- **Variables & Data Types:** `timeout`, `start_time`, `temp_path`, `lock_file`.

### research_historian.py (AI Telemetry & Long-Term Market Edge)
**What the code is actively doing:**
This file serves as a dedicated historical ledger separate from actual trading. It is responsible for logging "Shadow Trades" (paper setups for backtesting), "Near Misses" (reasons setups were rejected), and "Market Regimes". This provides the foundational data for future walk-forward learning.
- **Execution Flow & Internal Functions:**
 - `_init_db(self)`: Connects to `research_journal.db` (falling back to this name if configuration is absent) and establishes three tracking tables: `shadow_trades`, `market_regimes`, and `near_misses`.
 - `log_near_miss(self, miss_data)`: Logs a row into `near_misses` noting exactly why the AI chose *not* to trade a pair. It logs the combined ticker, the rejection `reason`, the statistical `zscore`, and the AI's textual `synthesis`.
 - `log_shadow_trade(self, trade_data)`: Logs theoretical trades into `shadow_trades` complete with parameters like `red_team_audit`, `ai_conviction`, `zscore`, and dual entry prices (`entry_price_a`, `entry_price_b`).
 - `log_regime_interpretation(self, macro_tensor, interpretation)`: Saves the AI's textual perception of current macro conditions (e.g. inflation data, global trends) into the `market_regimes` table.
 - `prune_old_data(self, window_days=30)`: Triggers a cleanup routine that calculates a datetime `cutoff` (`datetime.now() - timedelta(days=window_days)`). It executes `DELETE` statements on historical tables to wipe data older than the lookback window, actively preventing "Information Decay" and keeping the system focused on the current market state.
- **Variables & Data Types:** `miss_data`, `trade_data`, `cutoff`.

### bayesian_self_auditor.py (Bayesian Confidence Calibration)
**What the code is actively doing:**
This file statistically bridges the gap between the AI's *subjective* confidence (Scale 1 to 5) and the *empirical* market reality (Actual Win Rate). It uses Bayesian probability updating to dynamically adjust expected win probabilities, ensuring position sizing algorithms (like the Kelly Criterion) aren't fed over-optimistic or hallucinatory data.
- **Execution Flow & Internal Functions:**
 - `__init__(self)`: Sets up a `base_win_rates` dictionary `self.base_win_rates = {1: 0.35, 2: 0.45, 3: 0.50, 4: 0.58, 5: 0.65}`, which act as the initial "Bayesian Priors".
 - `get_realized_edge(self)`: 
  - Retrieves the full history from `trade_journal.json` using `atomic_read_json`.
  - Filters out open trades, keeping only resolved entries with an "outcome" and "confidence_level".
  - If total historical trades are less than 10, it safely aborts and returns the `base_win_rates`.
  - Iterates through each confidence level (1 through 5), collecting trades that fall into that specific bucket.
  - **Mathematical Blending (Bayesian Update):** 
   - Calculates the pure empirical win rate: `wins / len(level_trades)`
   - Calculates a confidence weight bounded by a maximum of 1.0 (Full confidence achieved at 50 trades): `weight = min(1.0, len(level_trades) / 50)`
   - Blends the Realized Rate with the Prior Rate: `blended = (rate * weight) + (self.base_win_rates[level] * (1 - weight))`
  - Rounds the blended probability to 3 decimal places and stores it back in a dictionary, logging the updated expectations before returning them.
- **Mathematical Formulas Used:**
 - Empirical Win Rate ($R$): $\frac{Wins_{Level}}{Total Trades_{Level}}$
 - Confidence Weight ($W$): $min(1.0, \frac{Total Trades_{Level}}{50})$
 - Blended Bayesian Probability: $(R \times W) + (Base Prior \times (1 - W))$
- **Variables & Data Types:** `level_trades`, `weight`, `blended`, `rate`, `realized_rates`.

### evolution_engine.py (Automated Strategy Weight Allocation)
**What the code is actively doing:**
This file is the "Capital Allocator" of the AI. It routinely executes 'Walk-Forward' backtests over the last 30 days of actual market data, scoring the theoretical performance of different underlying algorithms in `STRATEGY_MAP`. It then redistributes available capital (weights) towards the strategies that are actively working in the current market regime.
- **Execution Flow & Internal Functions:**
 - `run_weekly_evolution(self)`: 
  - Pulls standard asset tickers from configuration and initializes an empty `performance` dictionary.
  - Iterates through the strategies imported from `STRATEGY_MAP`.
  - Fetches the last 30 days of market data via `get_live_market_data` for each configured ticker on a 60-minute timeframe.
  - Initializes `StrategySimulator` (from `offline_backtest.py`) with a base $1000 balance.
  - Loops continuously from row index 50 to the end of the dataframe, simulating real-time walk-forward data injection by slicing the dataframe (`window = df.iloc[:i]`). 
  - Passes the `window` to the strategy to query a signal. If a signal fires, it initiates a simulated trade risking exactly $10 per setup. If a trade is active, it calls `sim.update()` with live `Close` and `ATR_14` metrics to simulate trailing stops or targets.
  - Summarizes the total PnL shift from the starting $1000 and registers it to the `performance` mapping for that strategy.
  - Calls `_update_allocator_weights(performance)` to act on the data.
 - `_update_allocator_weights(self, performance)`:
  - Takes the performance dictionary and calculates total positive expectancy by summing all non-negative values: `sum(max(0, v) for v in performance.values())`.
  - If total profits are $\leq 0$ across the board, it defaults strictly to an even distribution (`0.33` each, assuming 3 strategies).
  - **Mathematical Allocation**: If profitable, it assigns dynamic capital weights proportional to profit ratio, enforcing a hard floor of 0.1 (10%) per strategy to prevent total starvation: `new_weights = {k: max(0.1, v / total_pl)}`.
  - Inserts the newly calculated weight mappings directly into the SQLite `system_state` table for the live trading system to query.
- **Mathematical Formulas Used:**
 - Strategy Weight Allocation: $max\left(0.1, \frac{Strategy Profit_{Positive Only}}{Total Net Profit_{Positive Only}}\right)$
- **Variables & Data Types:** `performance`, `df`, `window`, `total_pl`, `new_weights`.

### strategy_auditor.py (Systemic Meta-Learning & Bias Detection)
**What the code is actively doing:**
This script evaluates the AI's most recent trade performance to spot systemic failure patterns. Instead of analyzing individual tickers, it checks the aggregate outcome of the last 10 trades to diagnose behavioral flaws (e.g., getting repeatedly chopped out, revenge trading, or setting stops too tight) and provides immediate actionable feedback text.
- **Execution Flow & Internal Functions:**
 - `generate_systemic_bias_report(self)`:
  - Connects to `trading_state.db` and queries the last 10 trades where an `outcome` exists (Completed trades only).
  - Splits the results into two list comprehensions based on "W" (Win) and "L" (Loss) classifications.
  - Generates the base text report noting the raw empirical win rate: `len(wins)*10%`.
  - **Critical Bias Detection:** If `len(losses) >= 5` (a 50% or worse failure rate), it flags a systemic failure and proceeds to sub-audit the reasons.
  - Extracts the `exit_reason` from the losing trades.
   - If "STOP_LOSS" triggers $> 3$ times, it concludes the AI is placing stops inside the market noise threshold and advises avoiding low-ADX regimes.
   - If "TRAILING_STOP" triggers $> 3$ times, it deduces the bot is giving back unrealized profits and advises shifting target acquisition aggressively.
  - **Revenge Trading Check:** Iterates the asset tickers of the recent 10 trades. If it discovers that all trades occurred across $< 3$ unique assets, it logs a "Revenge Trading" over-concentration warning advising diversification.
  - Returns the compiled markdown string.
- **Variables & Data Types:** `history`, `wins`, `losses`, `reasons`, `assets`, `report`.

---

## 6. System Health, Risk Overlay & Operations

### deadmans_switch_server.py (VPS Dead-Man's Switch Server)
**What the code is actively doing:**
This script runs as a Flask web server (intended for a VPS) that acts as a continuous watchdog for the trading system's connection. It expects regular pings (heartbeats) from the home PC. If the home PC crashes or loses connection, this server executes an emergency sequence.
- **Execution flow:**
 - The script initializes a Flask app (`app`) and spins up a background daemon thread running `watchdog_loop()`.
 - The Flask server listens on port 5000 (`/heartbeat` endpoint) for incoming HTTP POST requests from the local machine.
 - When a heartbeat is received, it updates the `last_heartbeat_time` global variable to the current system time and resets the `emergency_triggered` flag if the system was recovering.
 - Meanwhile, the `watchdog_loop` thread endlessly checks the difference between the current time and `last_heartbeat_time`.
 - If the elapsed time exceeds `HEARTBEAT_TIMEOUT` (90 seconds) and the emergency sequence hasn't already been triggered, it calls `close_all_positions()`.
 - `close_all_positions()` instantiates an Alpaca `TradingClient`, sends a command to immediately close all active positions and cancel all pending orders, and flags `emergency_triggered = True` to prevent repeated execution.
- **Internal functions:** `close_all_positions()`, `watchdog_loop()`, `heartbeat()`.
- **Mathematical formulas used:** 
 - Time elapsed calculation: $Diff = Time_{current} - Time_{last\_heartbeat}$
- **Variables:** `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `HEARTBEAT_TIMEOUT` (default 90s), `PORT` (5000), `last_heartbeat_time`, `emergency_triggered`, `diff`.

### heartbeat_monitor.py (Central Systemic Health Watchdog)
**What the code is actively doing:**
This is the main internal health supervisor running on the local PC. It continuously probes critical local and third-party dependencies (like the local Ollama LLM and the Alpaca API). If any dependency fails, it logs a critical failure and updates the database to prevent further trades.
- **Execution flow:**
 - Initializes the `HeartbeatMonitor` class with a target list of `critical_services` and a 30-second `check_interval`.
 - Executes `run_pulse_check()` which enters an infinite `while True` loop.
 - It tests the availability of Ollama via HTTP request and Alpaca via the API client.
 - If *any* test fails (`not all(health.values())`), it constructs an alert message detailing which service dropped, logs it as critical, dispatches a notification via the `Notifier` class, and sets the `system_health` state in the SQLite `TradingDatabase` to `CRITICAL_FAIL`.
 - If healthy, it sets the DB state to `HEALTHY` and updates the timestamp, then sleeps for 30 seconds.
- **Internal functions:** `check_local_llm()`, `check_alpaca_connectivity()`, `run_pulse_check()`.
- **Variables:** `self.critical_services`, `self.check_interval`, `health` (dictionary storing boolean states of services), `failed` (list of failed service names).

### heartbeat_sender.py (Local PC to VPS Heartbeat Sender)
**What the code is actively doing:**
This is the client-side counterpart to `deadmans_switch_server.py`. It runs on the local PC and is responsible for transmitting the periodic pulses to the VPS to prove the local machine is alive and functional.
- **Execution flow:**
 - Instantiates the `HeartbeatSender` class, pulling the target `DEADMAN_SWITCH_URL` from environment variables.
 - Calls `send_heartbeat()`, entering an infinite loop that triggers every 30 seconds (`self.interval`).
 - Inside the loop, it issues an HTTP POST request carrying a JSON payload (`{"status": "ALIVE"}`) to the VPS endpoint.
 - Catches exceptions and logs warnings if the HTTP request times out or returns a non-200 code.
- **Internal functions:** `send_heartbeat()`.
- **Variables:** `self.vps_url`, `self.interval` (30s).

### global_risk_overlay.py (Global Risk & Correlation Monitor)
**What the code is actively doing:**
Acts as the final safeguard before trade execution, preventing "The Isolation Paradox" (where individual trades look good, but collectively over-expose the portfolio to a single risk factor). It specifically limits portfolio-wide exposure to any single currency (e.g., USD).
- **Execution flow:**
 - When evaluated, `is_trade_allowed()` is called with the target `ticker` and proposed `risk_amount`.
 - It fetches all currently open trades from `trade_journal.json` using an atomic read function.
 - For each open trade, it dissects the asset into its base components (e.g., `EURUSD` -> `EUR`, `USD`) and tallies the total `risk_val` per currency.
 - It calculates the absolute dollar maximum allowable risk per currency (`account_balance * max_currency_exposure_pct`).
 - If adding the proposed trade's `risk_amount` to the current exposure of *any* involved component breaches the ceiling limit, the trade is vetoed.
- **Internal functions:** `get_active_exposure()`, `_get_asset_components(asset)`, `is_trade_allowed(...)`.
- **Mathematical formulas used:**
 - Aggregated Component Exposure: $E_{comp} = \sum RiskVal_{open\_trades}(comp)$
 - Exposure Ceiling: $Ceiling_{usd} = AccountBalance \times MaxCurrencyExposurePct$
 - Veto Check: $(E_{comp} + ProposedRisk) > Ceiling_{usd}$
- **Variables:** `max_currency_exposure` (0.03 or 3%), `journal_path`, `exposure` dictionary, `ceiling`, `components`.

### system_health.py (Unified System Health Monitor)
**What the code is actively doing:**
Consolidates macro-economic market conditions and physical network connectivity into a single "Go/No-Go" status check. It acts to halt trading if volatility is too high, the USD is spiking, or API ping latency is unacceptable.
- **Execution flow:**
 - The primary method `audit_system_readiness()` initializes a safe status report.
 - It first calculates network latency via shell ping to Alpaca. If latency is > 350ms, it degrades status and appends a veto.
 - It fetches market weather via Polygon API (or yfinance fallback) for DXY, VIX, US10Y, SPY. 
 - It enforces two macro rules: Vetoes LONG trades if VIX > 30. Vetoes LONG trades involving USD if DXY spiked > 0.5% in the last 5 hours.
 - Returns a boolean `is_safe` and a detailed report.
- **Internal functions:** `check_network_latency()`, `get_macro_weather()`, `audit_system_readiness()`.
- **Mathematical formulas used:**
 - 5-Hour Macro Change: $Change_{pct} = \frac{Close_{latest} - Close_{t-5}}{Close_{t-5}}$
- **Variables:** `target_host`, `max_ping_ms` (350), `strict_mode`, `latency`, `weather` data payload, `report` dictionary, `vix_price`, `dxy_move`.

### token_tracker.py (LLM API Cost & Spend Tracker)
**What the code is actively doing:**
Monitors and logs API costs incurred by the LLMs (Anthropic/Google). It guarantees the system halts API interactions if daily expenses breach a strict budget.
- **Execution flow:**
 - Whenever an LLM call finishes, `track_token_usage()` is invoked with input/output token counts and the model name.
 - It retrieves per-million-token prices from a `PRICING` dictionary (using accurately modeled 2026 prices).
 - It reads `billing_guard.json`, calculates the dollar cost of the current query, and increments the day's total cost, input tokens, output tokens, and call count.
 - Before executing new LLM prompts, the system calls `check_killswitch()`. If the day's total cost exceeds `limit` ($2.00 by default), it logs a critical failure and returns `True` to block the call.
- **Internal functions:** `track_token_usage()`, `check_killswitch()`.
- **Mathematical formulas used:**
 - Cost Calculation: $Cost_{usd} = (\frac{InputTokens}{1,000,000} \times InputRate) + (\frac{OutputTokens}{1,000,000} \times OutputRate)$
- **Variables:** `PRICING` reference table, `BILLING_FILE`, `model_pricing`, `daily_spend`, `today` string, `limit`.

### utils.py (System Utilities)
**What the code is actively doing:**
Provides standardized configurations for the broader system, notably JSON-formatted logging (useful for ingestion by external log aggregators like ELK or Datadog) and API retry logic.
- **Execution flow:**
 - When scripts call `setup_logging()`, it attaches two handlers to the logger: a `RotatingFileHandler` (max 5MB, keeps 3 backups) configured with custom JSON formatting, and a standard `StreamHandler` outputting plain text to the console.
 - Provides `retry_with_backoff`, a decorator for critical API functions. When decorated functions trigger specific Google API exceptions (like rate limits or server errors), the wrapper catches the error, sleeps, and retries the function call with progressively longer delays.
- **Internal functions:** `JsonFormatter.format()`, `setup_logging()`, `retry_with_backoff()`.
- **Mathematical formulas used:**
 - Exponential Backoff: $Delay_{next} = Delay_{current} \times BackoffFactor$
- **Variables:** `max_bytes` (5MB), `backup_count` (3), `retries`, `delay`, `initial_delay` (2), `backoff_factor` (2).

### notifier.py (Notification System)
**What the code is actively doing:**
Serves as the unified communications hub for the bot. It dispatches alerts (Infos, Trades, Errors) to Telegram and Discord. Crucially, it manages Human-In-The-Loop (HITL) approval mechanics.
- **Execution flow:**
 - Initializes using tokens fetched via `dotenv`. Disables functionality if none are found.
 - The `notify()` method takes a message and a type (INFO, TRADE, ERROR, CRITICAL), prefixes it with an emoji, and sequentially fires POST requests to Telegram and Discord webhooks.
 - The `wait_for_approval()` method is a blocking function. It sends a Telegram message with Inline Keyboard buttons (" FIRE", " VETO"). It then enters a polling loop on Telegram's `/getUpdates` endpoint, scanning for callback data matching those buttons. It will wait up to `timeout` (3600 seconds) for a user to press a button before defaulting to VETO.
- **Internal functions:** `send_telegram()`, `send_discord()`, `wait_for_approval()`, `notify()`, `get_log_tail()`, `send_log_tail()`.
- **Mathematical formulas used:**
 - Timeout expiry check: $Time_{now} - Time_{start} < Timeout$
- **Variables:** `telegram_token`, `discord_webhook_url`, `alert_type`, `updates` payload, `decision`.

### priority_queue.py (Opportunity Ranking Queue)
**What the code is actively doing:**
Manages an intelligent opportunity funnel. Instead of trading every signal as they arrive, it queues them up in a Min-Heap data structure. Each signal is scored based on mathematical criteria, and the bot pops the absolute highest scoring setup ("God-Tier Alpha") to trade first.
- **Execution flow:**
 - Initializes an `AlphaQueue` wrapping a Python list using the `heapq` module. Since `heapq` is a min-heap, scores are pushed as negative numbers to mimic a max-heap (highest scores float to the top).
 - When `push()` is called, it assigns a weight multiplier (e.g., doubling the score if the strategy is `CONTRARIAN_TRAP`). It then pushes the tuple `(-score, timestamp, ticker, strat_id, context)` into the queue. If the queue is full (default max 10), it replaces the lowest-tier setup using `heapreplace` if the new setup scores higher.
 - `pop_best()` returns the highest priority item and removes it from the heap.
 - `calculate_alpha_score()` computes the base score.
- **Internal functions:** `AlphaQueue.push()`, `AlphaQueue.pop_best()`, `calculate_alpha_score()`.
- **Mathematical formulas used:**
 - Strategy Weighting: $WeightedScore = Score \times Weight$
 - Proximity Factor: $ProxScore = \max(0, 50 \times (1 - \frac{\min(DistToHigh, DistToLow)}{ATR}))$
 - Spread/Execution Penalty: $SpreadToAtr = \frac{Price \times (SpreadBps / 10000)}{ATR}$. Bonus given if $SpreadToAtr < 0.12$.
 - Alpha Score: $Total = ProxScore + ExecBonus + \min(20, ADX)$
- **Variables:** `self.queue`, `max_size`, `strategy_weight`, `atr`, `adx`, `spread_to_atr`, `exec_bonus`.

### hustle_fund_manager.py (Treasury and Goal Tracker)
**What the code is actively doing:**
Acts as a holistic portfolio and "life" dashboard. It tracks the bot's trading capital, the user's index fund treasury, progress towards scaling to a Prop Firm challenge ($50k), and evaluates the "Opportunity Cost" of coding the bot versus just doing normal work.
- **Execution flow:**
 - Initializes `HustleFundManager` parsing `config.yaml` for fund targets and current holdings.
 - `get_treasury_value()` cycles through configured index fund holdings, pulls live day-prices via `get_live_market_data`, and totals their value.
 - `get_fund_dashboard()` merges trading balance and treasury into a `total_fund` value, computing the percentage complete toward the `target_capital`.
 - `get_prop_firm_readiness()` connects to the local `research_journal.db` SQLite database, sums all recorded paper-trading P&L (`slippage_adj_pnl`), and calculates if the algorithm is mathematically ready to attempt a Prop Firm challenge.
 - `get_time_value_audit()` calculates if the time spent maintaining the bot was financially worth it compared to a standard hourly wage.
 - `format_dashboard_text()` converts these metrics into a clean Telegram markdown string.
- **Internal functions:** `get_treasury_value()`, `get_fund_dashboard()`, `get_prop_firm_readiness()`, `get_time_value_audit()`, `format_dashboard_text()`.
- **Mathematical formulas used:**
 - Treasury Total: $Total_{treasury} = \sum (Holdings_{units} \times Price_{current})$
 - Prop Firm P&L: $NetPnL = \sum SlippageAdjPnL_{shadow\_trades}$
 - Time ROI Ratio: $EfficiencyRatio = \frac{TradingProfit}{HoursSpent \times HourlyWage}$
- **Variables:** `trading_balance`, `target` (default 10000), `holdings`, `net_pnl`, `user_wage` (default 25.0), `hours_spent` (40.0), `ratio`, `progress_pct`.

---

## Included Execution Logs (`todo.md`)

## All Roadmap Phases (1-82) Completed
The AiTradingBot has reached its **Full Architectural Potential** as of May 31, 2026. The system is now in its **Terminal Hardened State**. All core features have been mathematically and functionally integrated.

- [x] **Phase 1-20: Foundation, Pro-Grade Hardening, and Alpha Generation.**
 - **Mechanics:** Established the baseline `master_orchestrator.py` event loop. Integrated Alpaca API via `cro_risk.py` for direct market access.
 - **Metrics:** Replaced simple threshold strategies with `CorrelationArbitrageEngine` (Z-Score > 3.0) and `FundamentalDivergence` scanners.
 - **Failsafes:** Implemented atomic file locking (`atomic_ops.py`) and SQLite data persistence (`database_manager.py`) to prevent JSON corruption during multi-threaded execution.

- [x] **Phase 21-60: Institutional Deepening, Asymmetric Entry, and Autonomous Consensus.**
 - **Mechanics:** Shifted from immediate market execution to passive VWAP-anchored limit orders via `AsymmetricEntryOptimizer`. 
 - **Metrics:** Activated `bayesian_self_auditor.py` to continuously adjust the AI's internal confidence based on real-world empirical win rates. Deployed the `HarvardConsensusEngine` to blend retail positioning (DailyFX) with live LLM (Gemini 1.5) sentiment scoring.
 - **Failsafes:** Integrated OANDA WebSocket (`price_watch.py`) for millisecond-level mid-price stop-loss execution, bypassing local loop delays.

- [x] **Phase 61-82: Terminal Sovereign State, Infrastructure Health Gates, and News Divergence.**
 - **Mechanics:** Deployed the `deadmans_switch_server.py` VPS watcher and local `heartbeat_monitor.py` to ensure local LLM (Llama 3.1) and API gateways remain 100% online.
 - **Metrics:** Implemented `news_sentinel.py` to dynamically weigh information asymmetry, ensuring trades are blocked if extreme contrary news is published within the last 24 hours.
 - **Failsafes:** Set up `global_sentinel.py` to dynamically monitor 5-hour rate-of-change for DXY, VIX, and US10Y to enforce hard vetoes (e.g., blocking LONGs if VIX > 30).

## Current Active Phase: 12-Month Shadow Lock
The system is hard-locked into **Paper Trading Mode** to build a verifiable institutional track record.

- [x] **12-Month Shadow Lock**: Locked until May 2027 to ensure statistical edge (Phase 81).
 - **Mechanics:** Hardcoded logic gate in `5_trading_bot.py` specifically intercepting the system clock. Execution of `finalize_trade_execution()` is permanently skipped until the `datetime` module resolves > May 1, 2027. Trades are exclusively routed to `log_shadow_trade()`.
- [x] **Hustle Priority Gate**: Integration with career income and index fund management (Phase 82).
 - **Mechanics:** The `HustleFundManager` actively polls index fund asset values and contrasts the bot's P&L against the user's base hourly wage ($25/hr) to calculate the "Opportunity Cost ROI" of algorithmic management vs. traditional employment.
- [] **Autonomous Research**: Continuous logging of AI reasoning vs. market reality.
 - **Mechanics:** `research_historian.py` permanently saves "Near Misses" (with exact statistical Z-scores and LLM synthesis) alongside completed Shadow Trades to a dedicated `research_journal.db`. It automatically runs `prune_old_data` (30-day cutoff) to prevent information decay.
- [] **Slippage Stress-Testing**: Constant 10bps penalty enforcement.
 - **Mechanics:** Inside `offline_backtest.py`, synthetic friction is applied to all entries and exits ($Friction Factor = 1 \pm 0.0045$). This forces the mathematical models to prove edge against "The Truth of the Tape" rather than idealized mid-prices.

## Future Milestones (Post-May 2027)
- [ ] **Prop Firm Launch**: Purchase and execute a $100,000 challenge once the Shadow Fund reaches READY status.
 - **Mechanics:** Once `get_prop_firm_readiness()` confirms aggregate Shadow P&L exceeds $10,000 natively without drawdown violations, the Alpaca Paper keys will be rotated out for Prop Firm MetaTrader API credentials.
- [ ] **IBKR Pro DMA Migration**: Switch from paper to Live DMA execution for institutional scaling.
 - **Mechanics:** Phase out REST API HTTP calls. Replace `cro_risk.py`'s Alpaca module with the FIX Protocol/TWS API for direct market access (DMA) routing to minimize execution milliseconds.

---
*Last Updated: 2026-06-01 - Status: Architectural Finality.*
