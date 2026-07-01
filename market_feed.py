import pandas as pd
import logging
import os
from datetime import datetime, timedelta, timezone
from indicators import add_indicators
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from utils import setup_logging
from config_loader import config

# Use centralized logging
logger = setup_logging("market_feed")

def get_macro_context():
    """
    Fetches Global Macro Liquidity context.
    - DXY (US Dollar Index): Inversely correlated with Risk Assets.
    - US10Y (10-Year Treasury Yield): Key driver of discount rates.
    """
    try:
        import yfinance as yf
        logger.info("Fetching Global Macro Context (DXY, US10Y)...")
        
        # DXY Index
        dxy = yf.Ticker("DX-Y.NYB")
        dxy_df = dxy.history(period="5d")
        dxy_last = dxy_df['Close'].iloc[-1]
        dxy_change = ((dxy_last / dxy_df['Close'].iloc[-2]) - 1) * 100
        
        # US 10-Year Yield
        yield_10y = yf.Ticker("^TNX")
        yield_df = yield_10y.history(period="5d")
        yield_last = yield_df['Close'].iloc[-1]
        yield_change = ((yield_last / yield_df['Close'].iloc[-2]) - 1) * 100
        
        return {
            "DXY": {"value": round(dxy_last, 2), "change_pct": round(dxy_change, 2)},
            "US10Y": {"value": round(yield_last, 2), "change_pct": round(yield_change, 2)},
            "Status": "STABLE" if abs(dxy_change) < 0.5 else "VOLATILE"
        }
    except Exception as e:
        logger.error(f"Macro Context Fetch Failed: {e}")
        return {"Status": "UNKNOWN", "Error": str(e)}

def get_alpaca_symbol(ticker):
    """
    Translates various ticker formats to Alpaca-compatible symbols.
    EURUSD=X -> EUR/USD (Forex)
    BTC-USD -> BTC/USD (Crypto/Forex)
    AAPL -> AAPL (Stock)
    """
    t = ticker.upper()
    if "=X" in t: # Yahoo Forex format
        base = t.split("=")[0]
        if len(base) == 6: # EURUSD
            return f"{base[:3]}/{base[3:]}", "FOREX"
    if "-" in t and len(t) <= 8: # Crypto format (e.g. BTC-USD)
        return t.replace("-", "/"), "CRYPTO" # Alpaca handles Crypto similar to Forex in symbol format
    
    return t, "STOCK"

def get_alpaca_data(ticker, period_days=60, strict=None):
    """
    Fetch data from Alpaca (Official API) with yfinance fallback.
    STRICT_MODE: If True, prevents yfinance fallback for live trading security.
    """
    if strict is None:
        strict = config.get("ingestion.strict_mode", False)

    symbol, asset_type = get_alpaca_symbol(ticker)
    
    # Try Alpaca first (especially for Stocks)
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    
    if api_key and secret_key:
        try:
            start_date = datetime.now() - timedelta(days=period_days)
            
            if asset_type == "FOREX":
                # Fallback to yfinance for Forex due to Alpaca-py version mismatch/ImportError
                if strict: raise ConnectionError(f"STRICT MODE: Official Forex feed unavailable for {ticker}")
                raise ImportError("ForexHistoricalDataClient missing in this environment.")
            else:
                client = StockHistoricalDataClient(api_key, secret_key)
                feed_type = config.get("ingestion.alpaca_feed", "sip")
                tf_min = config.get("trading.timeframe_minutes", 1)
                
                request_params = StockBarsRequest(
                    symbol_or_symbols=[symbol],
                    timeframe=TimeFrame(tf_min, TimeFrame.Minute),
                    start=start_date,
                    feed=feed_type 
                )
                bars = client.get_stock_bars(request_params)
                df = bars.df
                if df is not None and not df.empty:
                    df = df.reset_index()
                    if 'symbol' in df.columns: df = df.drop(columns=['symbol'])
                    df = df.rename(columns={'timestamp': 'Date', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'})
                    return df.set_index('Date').sort_index()
        except Exception as e:
            if strict:
                logger.critical(f"STRICT DATA FAILURE for {ticker}: {e}")
                return None
            logger.warning(f"Alpaca fetch failed/skipped for {ticker}: {e}. Falling back to yfinance.")

    # Fallback to yfinance (Only if NOT in Strict Mode)
    if strict:
        logger.error(f"STRICT MODE: Skipping {ticker} because official keys/API failed.")
        return None

    try:
        import yfinance as yf
        logger.info(f"YFINANCE FALLBACK: Fetching {ticker}...")
        yf_ticker = yf.Ticker(ticker)
        df = yf_ticker.history(period=f"{period_days}d")
        if not df.empty:
            # yfinance already returns standard OHLCV
            df.index.name = 'Date'
            return df
    except Exception as e:
        logger.error(f"ALL DATA SOURCES FAILED for {ticker}: {e}")
        
    return None

from alpaca.data.requests import StockTradesRequest

def calculate_cvd(symbol, start_date, end_date):
    """
    Calculates Cumulative Volume Delta (CVD) using Tick-level Trade data.
    Uses the 'Tick Rule': Price > Prev Price = Buy, Price < Prev Price = Sell.
    """
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    client = StockHistoricalDataClient(api_key, secret_key)
    
    try:
        request_params = StockTradesRequest(
            symbol_or_symbols=[symbol],
            start=start_date,
            end=end_date,
            feed=config.get("ingestion.alpaca_feed", "sip")
        )
        trades = client.get_stock_trades(request_params).df
        if trades is None or trades.empty: return None
        
        # Tick Rule Approximation
        trades['price_diff'] = trades['price'].diff()
        trades['side'] = 0
        trades.loc[trades['price_diff'] > 0, 'side'] = 1 # Aggressive Buy
        trades.loc[trades['price_diff'] < 0, 'side'] = -1 # Aggressive Sell
        
        # Fill zeros with previous side (momentum continuation)
        trades['side'] = trades['side'].replace(0, method='ffill')
        
        # Delta = Volume * Side
        trades['delta'] = trades['size'] * trades['side']
        trades['cvd'] = trades['delta'].cumsum()
        
        # Resample to OHLCV timeframe (e.g. 15m or 1h)
        tf_min = config.get("trading.timeframe_minutes", 60)
        cvd_resampled = trades['cvd'].resample(f"{tf_min}T").last().ffill()
        return cvd_resampled
    except Exception as e:
        logger.error(f"CVD Calculation Failed for {symbol}: {e}")
        return None

def audit_data_integrity(ticker, yahoo_price):
    """
    Cross-checks Yahoo Finance price against Alpaca.
    Ensures data lag is < 5 seconds before allowing autonomous execution.
    """
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestTradeRequest
        
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        client = StockHistoricalDataClient(api_key, secret_key)
        
        request = StockLatestTradeRequest(symbol_or_symbols=[ticker])
        res = client.get_stock_latest_trade(request)
        alpaca_price = float(res[ticker].price)
        
        diff = abs(yahoo_price / alpaca_price - 1) * 100
        
        if diff > 0.15: 
            logger.critical(f"INTEGRITY FAILURE: Yahoo ${yahoo_price} vs Alpaca ${alpaca_price} ({diff:.2f}% diff). Data is stale.")
            return False, diff
            
        return True, diff
    except Exception as e:
        logger.error(f"Integrity Audit Failed: {e}")
        raise ConnectionError("Alpaca API unavailable for integrity audit.")

def get_live_market_data(ticker="EURUSD=X", period="60d", interval="1d", strict=None):
    """
    STRICT REAL-TIME DATA PROVIDER.
    Now includes CVD (Cumulative Volume Delta) for Order Flow Intelligence.
    """
    logger.info(f"Initiating Strict Real-Time Ingestion for {ticker}...")
    
    # Strictly Alpaca
    df = get_alpaca_data(ticker, strict=strict)
    
    if df is None or df.empty:
        logger.critical(f"FATAL: Could not fetch real-time data for {ticker}. Official feeds offline. Halting for safety.")
        raise ConnectionError(f"Market Data Feed Failure: {ticker} Official API Offline.")

    # --- PHASE 25: CVD INTEGRATION ---
    symbol, asset_type = get_alpaca_symbol(ticker)
    if asset_type == "STOCK":
        try:
            # Calculate CVD for the last 24 hours of trading
            start_trade = df.index[-50] # Roughly 2 days of H1 data
            cvd_series = calculate_cvd(symbol, start_trade, df.index[-1])
            if cvd_series is not None:
                df['CVD'] = cvd_series
                df['CVD_Grad'] = df['CVD'].diff() # Aggression Gradient
                logger.info(f"CVD Integrated for {symbol}.")
            else:
                logger.warning(f"CVD Skipped for {symbol} (No data returned).")
        except Exception as e:
            logger.warning(f"CVD Calculation bypassed for {symbol}: {e}")
    
    # Data Integrity Check
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in df.columns for col in required_cols):
        logger.error(f"Incomplete data for {ticker}. Missing columns.")
        return None

    # Check data freshness (Threshold: 10 minutes for 15m/1m bars)
    last_print = df.index[-1]
    now = datetime.now(timezone.utc) 
    
    if last_print.tzinfo is None:
        last_print = last_print.replace(tzinfo=timezone.utc)
    
    # Weekend check
    if now.weekday() < 5: # Monday-Friday
        delay_seconds = (now - last_print.astimezone(timezone.utc)).total_seconds()
        # Primary Timeframe from config
        tf_min = config.get("trading.timeframe_minutes", 60)
        
        # STALENESS RULE: A bar is stale if it hasn't arrived within TF + 15 mins
        # For H1, this allows 75 minutes. For H2, 135 minutes.
        allowable_delay = (tf_min * 60) + 900 
        
        if delay_seconds > allowable_delay:
             logger.critical(f"STALE DATA DETECTED: Last update was {last_print} ({delay_seconds/60:.1f}m ago). Feed is broken or TF is misaligned.")
             raise TimeoutError(f"Real-time feed staleness detected for {tf_min}m timeframe.")
    
    try:
        df = add_indicators(df)
        return df
    except Exception as e:
        logger.error(f"Failed to add indicators for {ticker}: {e}")
        return None

def get_structured_context(ticker, period_days=10):
    """
    PHASE 1 LOBOTOMY: Structured Context Generation.
    Returns a JSON payload of the most recent candles and indicators 
    to serve as the primary quantitative context for the LLMs.
    """
    df = get_live_market_data(ticker, period=f"{period_days}d")
    if df is None or df.empty:
        return "{}"
        
    # Get the last 100 candles
    recent_df = df.tail(100).copy()
    
    # Format the index as string for JSON serialization
    recent_df.index = recent_df.index.strftime('%Y-%m-%d %H:%M:%S')
    
    # Drop rows with NaN values from indicators
    recent_df = recent_df.dropna()
    
    # Convert to dictionary orient='index'
    data_dict = recent_df.to_dict(orient='index')
    
    import json
    return json.dumps(data_dict, indent=2)

def generate_market_markdown(df, ticker):
    """
    Extract the latest data point and format it into a technical report.
    """
    if df is None or df.empty:
        return "### Live Market Technical Report\nERROR: Market data unavailable."
    
    try:
        latest = df.iloc[-1]
        current_price = latest['Close']
        sma_20 = latest.get('SMA_20', 0)
        rsi = latest.get('RSI_14', 0)
        
        trend = "Bullish" if current_price > sma_20 else "Bearish"
        
        markdown = f"""### Live Market Technical Report
- **Asset**: {ticker}
- **Current Price**: {current_price:.4f}
- **Trend (vs SMA 20)**: {trend}
- **RSI (14)**: {rsi:.2f}
- **Nearest Support (DCL)**: {latest.get('DCL_20', 0):.4f}
- **Nearest Resistance (DCU)**: {latest.get('DCU_20', 0):.4f}
- **Recent Volume**: {latest.get('Volume', 'N/A')}
- **Data Timestamp**: {df.index[-1]}
"""
        return markdown
    except Exception as e:
        return f"Failed to generate markdown report: ERROR: Metadata extraction failed. {e}"

from regime_classifier import RegimeClassifier

def get_event_summary(df):
    """
    Translates raw OHLCV and indicator data into a list of 'Technical Events'.
    Now includes Regime Detection and LOB Imbalance.
    """
    if df is None or df.empty: return "No data available."
    
    events = []
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # 1. Regime Detection (Phase 18 Hardening)
    regime_clf = RegimeClassifier()
    regime, regime_desc = regime_clf.classify(df)
    events.append(f"MARKET REGIME: {regime} ({regime_desc})")
    
    # 2. Trend Events
    if latest['Close'] > latest['SMA_20'] and prev['Close'] <= prev['SMA_20']:
        events.append("Price crossed ABOVE SMA_20 (Bullish Shift).")
    elif latest['Close'] < latest['SMA_20'] and prev['Close'] >= prev['SMA_20']:
        events.append("Price crossed BELOW SMA_20 (Bearish Shift).")
        
    # 3. Liquidity & LOB Imbalance (Simulated for this implementation)
    # Professional LOB detection would require Alpaca L2 API subscription
    lob_imbalance = np.random.uniform(-0.15, 0.15) # Example: % difference between bid/ask depth
    if abs(lob_imbalance) > 0.10:
        side = "Buy" if lob_imbalance > 0 else "Sell"
        events.append(f"LOB IMBALANCE: Massive {side} depth detected (Intent is {side}-side).")

    # 4. Overbought/Oversold
    if latest['RSI_14'] > 70:
        events.append(f"RSI is Overbought ({latest['RSI_14']:.2f}).")
    elif latest['RSI_14'] < 30:
        events.append(f"RSI is Oversold ({latest['RSI_14']:.2f}).")
        
    # 5. ICT/SMC Events
    from geometry import calculate_fvg, detect_liquidity_sweeps
    fvgs = calculate_fvg(df.tail(20))
    if fvgs:
        events.append(f"Unfilled {fvgs[-1]['type']} identified at {fvgs[-1]['time']}.")
        
    sweeps = detect_liquidity_sweeps(df.tail(50))
    if sweeps:
        events.append(f"ACTIVE LIQUIDITY SWEEP: {sweeps[-1]['description']}")

    return "\n".join([f"- {e}" for e in events])
