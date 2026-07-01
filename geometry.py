import pandas as pd
import numpy as np

def calculate_swing_points(df, window=5):
    """
    Programmatically identify Swing Highs and Lows without lookahead bias.
    A swing point at index 'i' is only confirmed after 'window' bars have passed.
    """
    df = df.copy()
    # Find local extremes in a trailing window
    # A high at index i is a swing high if it's the max of [i-window, i+window]
    # In real-time, we check if the high at index 'i-window' was the max of [i-2*window, i]
    
    df['is_high'] = df['High'] == df['High'].rolling(window=window*2+1).max()
    df['is_low'] = df['Low'] == df['Low'].rolling(window=window*2+1).min()
    
    # Shift back by 'window' to mark the ACTUAL peak, but only if confirmed by future bars
    # This means the 'swing_high' column will have values 'window' bars in the past.
    df['swing_high'] = np.nan
    df['swing_low'] = np.nan
    
    # We mark the swing point at the actual peak index
    high_indices = df.index[df['is_high'].shift(-window) == True]
    low_indices = df.index[df['is_low'].shift(-window) == True]
    
    df.loc[high_indices, 'swing_high'] = df.loc[high_indices, 'High']
    df.loc[low_indices, 'swing_low'] = df.loc[low_indices, 'Low']
    
    return df.drop(columns=['is_high', 'is_low'])

def calculate_fvg(df):
    """Identify Fair Value Gaps (FVG) or Imbalances."""
    fvg_zones = []
    # Loop through to find 3-candle patterns
    for i in range(2, len(df)):
        # Bullish FVG (Gap between Candle 1 High and Candle 3 Low)
        if df['Low'].iloc[i] > df['High'].iloc[i-2]:
            timestamp = df.index[i-1]
            time_str = timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else str(timestamp)
            fvg_zones.append({
                "type": "BULLISH_FVG",
                "top": df['Low'].iloc[i],
                "bottom": df['High'].iloc[i-2],
                "time": time_str
            })
        # Bearish FVG (Gap between Candle 1 Low and Candle 3 High)
        elif df['High'].iloc[i] < df['Low'].iloc[i-2]:
            timestamp = df.index[i-1]
            time_str = timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else str(timestamp)
            fvg_zones.append({
                "type": "BEARISH_FVG",
                "top": df['Low'].iloc[i-2],
                "bottom": df['High'].iloc[i],
                "time": time_str
            })
    return fvg_zones[-5:] # Return only recent zones

def calculate_smt_divergence(df_primary, df_correlated):
    """
    Detects SMT (Smart Money Technique) Divergence between two correlated assets.
    Example: EURUSD makes a lower low, but GBPUSD makes a higher low.
    Uses trailing windows to avoid lookahead bias.
    """
    if len(df_primary) < 20 or len(df_correlated) < 20:
        return None
    
    # Use trailing min/max to avoid lookahead bias
    p_lows = df_primary['Low'].rolling(window=5).min()
    c_lows = df_correlated['Low'].rolling(window=5).min()
    
    p_highs = df_primary['High'].rolling(window=5).max()
    c_highs = df_correlated['High'].rolling(window=5).max()
    
    # Check for Bullish SMT (Lower Low on Primary vs Higher Low on Correlated)
    # Compare recent low vs a previous low (e.g., 10 bars ago)
    if p_lows.iloc[-1] < p_lows.iloc[-10] and c_lows.iloc[-1] > c_lows.iloc[-10]:
        return "BULLISH_SMT_DIVERGENCE"
    
    # Check for Bearish SMT (Higher High on Primary vs Lower High on Correlated)
    if p_highs.iloc[-1] > p_highs.iloc[-10] and c_highs.iloc[-1] < c_highs.iloc[-10]:
        return "BEARISH_SMT_DIVERGENCE"
        
    return None

def calculate_volume_delta(df):
    """
    Approximates Volume Delta (Order Flow) from OHLCV data.
    Measures the 'Intra-Candle' buying vs selling pressure.
    """
    # Simple Delta: (Close - Open) / (High - Low) * Volume
    # Professional Delta: Uses wick rejection to weight pressure
    range_val = (df['High'] - df['Low']).replace(0, 0.0001)
    # Buying pressure: Distance from Low to Close
    buy_pressure = (df['Close'] - df['Low']) / range_val
    # Selling pressure: Distance from High to Close
    sell_pressure = (df['High'] - df['Close']) / range_val
    
    delta = df['Volume'] * (buy_pressure - sell_pressure)
    return delta

def detect_liquidity_sweeps(df, window=20):
    """
    Identifies 'Stop Runs' where price sweeps a key level and reverses.
    This is the signature of institutional 'Smart Money' entries.
    """
    df = calculate_swing_points(df, window=5)
    highs = df['swing_high'].dropna()
    lows = df['swing_low'].dropna()
    
    if len(highs) < 2 or len(lows) < 2:
        return []

    latest = df.iloc[-1]
    sweeps = []
    
    # 1. Bearish Sweep (Liquidity Grab above previous high)
    # Current High > Previous Swing High AND Current Close < Previous Swing High
    prev_high = highs.iloc[-2]
    if latest['High'] > prev_high and latest['Close'] < prev_high:
        sweeps.append({
            "type": "BEARISH_LIQUIDITY_SWEEP",
            "level": prev_high,
            "description": "Price ran stops above Swing High and reversed (Reclaim)."
        })
        
    # 2. Bullish Sweep (Liquidity Grab below previous low)
    prev_low = lows.iloc[-2]
    if latest['Low'] < prev_low and latest['Close'] > prev_low:
        sweeps.append({
            "type": "BULLISH_LIQUIDITY_SWEEP",
            "level": prev_low,
            "description": "Price ran stops below Swing Low and reversed (Spring)."
        })
        
    return sweeps

def check_geometric_distance(point_a, point_b):
    """Calculates Euclidean distance between two price points (time ignored for simple checks)."""
    return np.sqrt((point_a - point_b)**2)

def calculate_volatility_floor(df, window=20):
    """
    Calculates the 'Noise Floor' based on Standard Deviation.
    Institutional stops should be placed outside the 2.5 Sigma range
    to avoid high-frequency probing (Stop Hunting).
    """
    returns = df['Close'].pct_change()
    std_dev = returns.rolling(window=window).std()
    
    # Floor in absolute price units (StdDev * Price)
    floor = df['Close'] * std_dev
    return floor.iloc[-1] if not floor.empty else 0

def calculate_volume_profile(df, bins=20):
    """
    Calculates Volume Profile to identify POC (Point of Control).
    Anchors 'Narrative' levels (FVG, Sweeps) in raw Volume-at-Price reality.
    """
    if df is None or df.empty: return 0, 0, 0
    
    price_min = df['Low'].min()
    price_max = df['High'].max()
    
    # Create price bins
    price_bins = np.linspace(price_min, price_max, bins + 1)
    
    # Use digitize to assign each candle to a bin based on typical price
    df['price_bin'] = np.digitize((df['High'] + df['Low'] + df['Close']) / 3, price_bins)
    
    # Group by bin and sum volume
    vprofile = df.groupby('price_bin')['Volume'].sum()
    
    if vprofile.empty: return 0, 0, 0
    
    poc_bin = vprofile.idxmax()
    poc_price = (price_bins[poc_bin-1] + price_bins[poc_bin]) / 2
    
    # Value Area (Rough 70% calculation)
    total_vol = vprofile.sum()
    vprofile_sorted = vprofile.sort_values(ascending=False)
    va_vol = 0
    va_bins = []
    for bin_idx, vol in vprofile_sorted.items():
        va_vol += vol
        va_bins.append(bin_idx)
        if va_vol >= total_vol * 0.70: break
        
    va_low = price_bins[min(va_bins)-1]
    va_high = price_bins[max(va_bins)]
    
    return poc_price, va_low, va_high

def detect_absorption(df, threshold_sigma=2.0):
    """
    Identifies 'Absorption' (High Effort, No Result).
    Occurs when large Volume Delta meets a small candle body.
    Signature of institutional players absorbing retail momentum.
    """
    if len(df) < 20: return []
    
    df = df.copy()
    df['delta'] = calculate_volume_delta(df)
    df['body_size'] = abs(df['Close'] - df['Open'])
    
    # Normalize Delta
    delta_mean = df['delta'].abs().mean()
    delta_std = df['delta'].abs().std()
    
    latest = df.iloc[-1]
    
    # Absorption Logic: 
    # Delta is > 2 Sigma AND Body Size is < Median body size
    is_high_delta = abs(latest['delta']) > (delta_mean + threshold_sigma * delta_std)
    is_small_body = latest['body_size'] < df['body_size'].tail(20).median()
    
    results = []
    if is_high_delta and is_small_body:
        side = "BULLISH_ABSORPTION" if latest['delta'] > 0 else "BEARISH_ABSORPTION"
        results.append({
            "type": side,
            "level": latest['Close'],
            "description": f"Institutional Absorption at {latest['Close']:.5f}. Retail {side.split('_')[0]} effort was blocked by a wall of orders."
        })
        
    return results

def get_geometric_anchors(df):
    """Synthesize mathematical geometry for Vision Agent anchoring."""
    df_swings = calculate_swing_points(df)
    last_high = df_swings['swing_high'].dropna().iloc[-1] if not df_swings['swing_high'].dropna().empty else 0
    last_low = df_swings['swing_low'].dropna().iloc[-1] if not df_swings['swing_low'].dropna().empty else 0
    fvgs = calculate_fvg(df)
    
    # Order Flow, Sweeps, and Absorption
    volume_delta = calculate_volume_delta(df).iloc[-1]
    sweeps = detect_liquidity_sweeps(df)
    absorption = detect_absorption(df)
    poc, va_low, va_high = calculate_volume_profile(df)
    
    # Distance checks for Trap detection
    dist_to_high = check_geometric_distance(df['Close'].iloc[-1], last_high)
    dist_to_low = check_geometric_distance(df['Close'].iloc[-1], last_low)
    
    anchor_text = f"MATH-ANCHORED GEOMETRY (Institutional Footprints):\n"
    anchor_text += f"- Order Flow (Volume Delta): {'Net Buying' if volume_delta > 0 else 'Net Selling'} ({volume_delta:.0f} units)\n"
    
    if sweeps or absorption:
        anchor_text += "- 🚨 INSTITUTIONAL SIGNATURES DETECTED:\n"
        for s in sweeps:
            anchor_text += f"  * {s['type']} at level {s['level']:.5f} ({s['description']})\n"
        for a in absorption:
            anchor_text += f"  * {a['type']} at level {a['level']:.5f} ({a['description']})\n"
    else:
        anchor_text += "- No active liquidity sweeps or absorption identified.\n"
        
    anchor_text += f"- Point of Control (POC): {poc:.5f}\n- Value Area: {va_low:.5f} - {va_high:.5f}\n"
    anchor_text += f"- Verified Swing High: {last_high:.5f}\n- Verified Swing Low: {last_low:.5f}\n"
    anchor_text += f"- Proximity to High: {dist_to_high:.5f}\n- Proximity to Low: {dist_to_low:.5f}\n"
    anchor_text += "- Recent Imbalances (FVGs):\n"
    for f in fvgs:
        anchor_text += f"  * {f['type']} at {f['time']} (Zone: {f['bottom']:.5f} - {f['top']:.5f})\n"
    
    return anchor_text
