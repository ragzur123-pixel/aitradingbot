import os
import json
import logging
import time
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import List, Optional
from market_feed import get_live_market_data
from sentiment_sentinel import HarvardConsensusEngine
from geometry import get_geometric_anchors
from utils import setup_logging
from risk_manager import check_market_regime

# Setup logging
logger = setup_logging("market_snapshot")

SNAPSHOT_FILE = "market_snapshot.md"

# --- Phase 9: Pydantic Validation Layer ---
class MarketDataSchema(BaseModel):
    ticker: str
    last_close: float = Field(gt=0)
    rsi: float = Field(ge=0, le=100)
    adx: float = Field(ge=0)
    atr: float = Field(ge=0)
    avg_volume_15m: float = Field(ge=0)
    sma_20: float = Field(gt=0)
    dcl: float = Field(gt=0)
    dcu: float = Field(gt=0)
    wotc_bias: float = Field(ge=-1.0, le=1.0)
    wotc_confidence: float = Field(ge=0, le=1.0)
    herd_status: str

    @field_validator('last_close', 'sma_20', 'dcl', 'dcu')
    @classmethod
    def check_non_zero(cls, v):
        if v == 0: raise ValueError("Price value cannot be zero")
        return v

def create_market_snapshot(ticker="EURUSD=X"):
    """
    Clockwork Snapshot Generation. 
    Now includes Pydantic Validation and Math-Anchored Geometry.
    """
    logger.info(f"Generating Mission-Critical Snapshot for {ticker}...")

    # 1. Pull Live Feeds
    df = get_live_market_data(ticker)
    if df is None: return False
    
    # --- Phase 18: MARKET REGIME FILTER (Safety Gate) ---
    is_trending, regime_msg = check_market_regime(df)
    if not is_trending:
        logger.info(regime_msg)
        return False # Halt pipeline for sideways markets
        
    logger.info(regime_msg)

    sentinel = HarvardConsensusEngine()
    crowd = sentinel.run_sentinel(ticker)
    
    latest = df.iloc[-1]
    
    # 2. Hard Geometry Anchors (Phase 5)
    geo_anchors = get_geometric_anchors(df)
    
    # --- Phase 18: VOLUME PROFILE (Liquidity Foundation) ---
    from geometry import calculate_volume_profile
    poc, va_low, va_high = calculate_volume_profile(df)

    # --- Phase 18: VOLATILITY FLOOR (HFT Shield) ---
    from geometry import calculate_volatility_floor
    vol_floor = calculate_volatility_floor(df)
    
    # --- Phase 18: ZERO-COST MATH GATE (Cost Optimization) ---
    # We only trigger the expensive AI analysts if we are at a "Point of Interest"
    last_close = float(latest['Close'])
    atr = float(latest.get('ATR_14', 0))
    
    # Extract distances from geo_anchors 
    from geometry import calculate_swing_points, check_geometric_distance, calculate_fvg, detect_liquidity_sweeps
    df_swings = calculate_swing_points(df)
    last_high = df_swings['swing_high'].dropna().iloc[-1] if not df_swings['swing_high'].dropna().empty else 0
    last_low = df_swings['swing_low'].dropna().iloc[-1] if not df_swings['swing_low'].dropna().empty else 0
    
    dist_to_h = check_geometric_distance(last_close, last_high)
    dist_to_l = check_geometric_distance(last_close, last_low)
    
    # Threshold: 1.0 * ATR for PoI proximity (Volatility Aware)
    threshold = atr if atr > 0 else (last_close * 0.002) 
    
    has_fvg = len(calculate_fvg(df)) > 0
    is_near_level = (dist_to_h < threshold) or (dist_to_l < threshold)
    has_sweeps = len(detect_liquidity_sweeps(df)) > 0
    
    if not (is_near_level or has_fvg or has_sweeps):
        logger.info(f"MATH GATE: No PoI detected (Dist to H: {dist_to_h:.5f}, Dist to L: {dist_to_l:.5f}, ATR Threshold: {threshold:.5f}).")
        logger.info("Skipping AI analysis to save costs. Strategic Skip.")
        import sys
        sys.exit(2) # Code 2: Strategic Skip (No POI)
    
    logger.info("MATH GATE: High-Probability Zone Detected. Proceeding to AI Analysis.")

    # 3. Pydantic Validation (Phase 9)
    avg_vol_15m = float(df['Volume'].iloc[-15:].mean())
    raw_payload = {
        "ticker": ticker,
        "last_close": float(latest['Close']),
        "rsi": float(latest.get('RSI_14', 50)),
        "adx": float(latest.get('ADX_14', 0)),
        "atr": float(latest.get('ATR_14', 0)),
        "avg_volume_15m": avg_vol_15m,
        "sma_20": float(latest.get('SMA_20', 0)),
        "dcl": float(latest.get('DCL_20', 0)),
        "dcu": float(latest.get('DCU_20', 0)),
        "wotc_bias": crowd['aggregated_bias'],
        "wotc_confidence": crowd['confidence'],
        "herd_status": crowd['herd_status']
    }

    try:
        validated_data = MarketDataSchema(**raw_payload)
    except ValidationError as e:
        logger.critical(f"CRITICAL: Pydantic Validation Error for {ticker}!")
        logger.critical(f"Raw payload: {json.dumps(raw_payload, indent=2)}")
        logger.exception(e)
        return False
    except Exception as e:
        logger.error(f"SCHEMA VALIDATION FAILED: {e}")
        # Halt pipeline as per Mission-Critical instructions
        import sys
        sys.exit(1)

    # 4. Construct Markdown "Source of Truth"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    snapshot_md = f"""# MISSION-CRITICAL MARKET SNAPSHOT
**Asset**: {validated_data.ticker}
**Generation Timestamp**: {timestamp}
**Data Integrity Status**: Pydantic-Verified ✅

---

## 1. RAW PRICE EVIDENCE
- **Last Close Price**: {validated_data.last_close:.5f}
- **Volume**: {latest['Volume']}
- **Avg 15m Volume**: {validated_data.avg_volume_15m:.0f}

## 2. CALCULATED TECHNICALS
- **RSI (14)**: {validated_data.rsi:.2f}
- **Market Regime (ADX 14)**: {validated_data.adx:.2f}
- **Volatility (ATR 14)**: {validated_data.atr:.5f}
- **Volatility Floor (2.5 Sigma)**: {vol_floor:.5f}
- **Liquidity POC (Volume Profile)**: {poc:.5f}
- **Value Area (70% Vol)**: {va_low:.5f} - {va_high:.5f}
- **Trend Baseline (SMA 20)**: {validated_data.sma_20:.5f}
- **Dynamic Support**: {validated_data.dcl:.5f}
- **Dynamic Resistance**: {validated_data.dcu:.5f}

---

## 3. MATH-ANCHORED GEOMETRY (Verified Structure)
{geo_anchors}

---

## 4. HARVARD WOTC SENTIMENT ORACLE
- **Aggregated Bias**: {validated_data.wotc_bias}
- **Herd Status**: {validated_data.herd_status}
- **Consensus Confidence**: {validated_data.wotc_confidence * 100}%

---

## STOP: AI USAGE RULES
1. Treat every value above as an immutable fact.
2. CITE SECTIONS (e.g., 'Per Section 3, verified swing low is...').
"""

    # Atomic Write
    temp_path = SNAPSHOT_FILE + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(snapshot_md)
    os.replace(temp_path, SNAPSHOT_FILE)

    logger.info(f"Verified Snapshot pinned to {SNAPSHOT_FILE}.")
    return True

if __name__ == "__main__":
    import sys
    create_market_snapshot(sys.argv[1] if len(sys.argv) > 1 else "EURUSD=X")
