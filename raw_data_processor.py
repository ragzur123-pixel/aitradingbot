import os
import json
import logging
import numpy as np
import pandas as pd
from utils import setup_logging

logger = setup_logging("raw_data_processor")

class RawDataProcessor:
    """Maps OHLCV and L2 data into numeric strings."""
    def __init__(self, window_size=100):
        self.window_size = window_size

    def prepare_macro_tensor(self, macro_dict):
        """
        Formats Global Macro Context for AI ingestion.
        DXY > US10Y relation is a key driver of asset regimes.
        """
        if not macro_dict or "DXY" not in macro_dict: return "MACRO_UNKNOWN"
        
        dxy = macro_dict["DXY"]
        tnx = macro_dict["US10Y"]
        
        macro_text = (
            f"MACRO_SNAPSHOT:\n"
            f"- DXY: {dxy['value']} ({dxy['change_pct']}%)\n"
            f"- US10Y: {tnx['value']}% ({tnx['change_pct']}%)\n"
            f"- SYSTEM_LIQUIDITY: {'TIGHTENING' if dxy['change_pct'] > 0.1 else 'EXPANDING' if dxy['change_pct'] < -0.1 else 'STABLE'}\n"
            f"- RISK_SENTIMENT: {'OFF' if tnx['change_pct'] > 0.5 and dxy['change_pct'] > 0 else 'ON' if dxy['change_pct'] < 0 else 'NEUTRAL'}"
        )
        return macro_text

    def prepare_1h_micro_tensor(self, df_1h, df_15m):
        """
        Provides a 'High-Res Internal Map' of the last 4 hours.
        For each 1H candle, it shows the 15m breakdown of Buying vs Selling aggression.
        """
        if df_1h is None or df_15m is None: return "ERR:NO_DATA"
        
        # We look at the last 4 1H candles
        recent_1h = df_1h.tail(4).index
        micro_data = []
        
        for h_time in recent_1h:
            # Filter 15m data that belongs to this 1H window
            h_start = h_time
            h_end = h_time + pd.Timedelta(minutes=59)
            sub_15m = df_15m.loc[h_start:h_end]
            
            if sub_15m.empty: continue
            
            # Calculate Internal Metrics
            # CVDR: Cumulative Volume Delta Ratio (Buy-Sell Aggression)
            # IVOL: Intra-candle Volatility (High-Low / Open)
            for i, (idx, row) in enumerate(sub_15m.iterrows()):
                cvdr = (row.get('CVD_Grad', 0) / row['Volume']) if row['Volume'] > 0 else 0
                ivol = (row['High'] - row['Low']) / row['Open']
                micro_data.append({
                    "1H_T": h_time.strftime('%H:00'),
                    "15M": f"Q{i+1}",
                    "CVDR": round(cvdr, 3),
                    "IVOL": round(ivol, 4),
                    "CLOSE": round(row['Close'], 2)
                })
        
        micro_df = pd.DataFrame(micro_data)
        header = "1H_T,15M,CVDR,IVOL,CLOSE"
        csv_body = micro_df.to_csv(header=False, index=False).strip()
        return f"{header}\n{csv_body}"

    def prepare_pair_tensor(self, df_a, df_b, beta):
        """
        Formats a 'Divergence Tensor' for Statistical Arbitrage.
        Shows how the Spread between Asset A and Asset B is behaving.
        """
        if df_a is None or df_b is None: return "ERR:NO_DATA"
        
        # Align
        combined = pd.concat([df_a['Close'], df_b['Close']], axis=1).dropna()
        combined.columns = ['A', 'B']
        
        # Calculate Rolling Spread and Z-Score
        log_a = np.log(combined['A'])
        log_b = np.log(combined['B'])
        spread = log_a - (beta * log_b)
        
        from indicators import calculate_zscore
        zscore = calculate_zscore(spread, window=20)
        
        pair_df = pd.DataFrame({
            "T": combined.index.strftime('%H:%M'),
            "A_Price": combined['A'].round(2),
            "B_Price": combined['B'].round(2),
            "Spread": spread.round(5),
            "ZScore": zscore.round(3)
        }).tail(30)
        
        header = "T,A_P,B_P,SPD,ZS"
        csv_body = pair_df.to_csv(header=False, index=False).strip()
        return f"{header}\n{csv_body}"

    def calculate_wick_rejection_delta(self, df):
        """Calculates a Wick Delta Technical Indicator (approximates absorption). Not real L3 data."""
        # Upper Wick: Selling Pressure (High - max(Open, Close))
        upper_wick = df['High'] - df[['Open', 'Close']].max(axis=1)
        # Lower Wick: Buying Pressure (min(Open, Close) - Low)
        lower_wick = df[['Open', 'Close']].min(axis=1) - df['Low']
        
        # Simulated Delta: Buying Wick Pressure - Selling Wick Pressure
        # Normalized by Body Size to find 'Absorption' (High Wick, Small Body)
        body_size = abs(df['Close'] - df['Open'])
        body_size = np.where(body_size < 1e-6, 1e-6, body_size)
        sim_delta = (lower_wick - upper_wick) / body_size
        return pd.Series(sim_delta, index=df.index).round(3)

    def prepare_compressed_tensor(self, df):
        """
        Converts OHLCV + Order Flow data into a ultra-lean CSV string.
        Columns: Time, Close_Pct, Vol_Ratio, RSI, Wick_Delta (Simulated L3), Accel
        """
        if df is None or len(df) < 50:
            return "ERR:NO_DATA"

        recent = df.tail(50).copy()
        base_price = recent['Close'].iloc[0]
        
        # 1. Normalize
        recent['CP'] = (recent['Close'] / base_price - 1) * 100 # Close Pct
        vol_mean = recent['Volume'].mean()
        recent['VR'] = (recent['Volume'] / vol_mean) if vol_mean > 1e-9 else 0.0 # Vol Ratio
        
        # Wick Delta Indicator Ingestion
        recent['WD'] = self.calculate_wick_rejection_delta(recent)
        recent['PA'] = recent['CP'].diff().diff() # Price Acceleration
        
        # 2. Select Columns and Round
        recent['T'] = recent.index.strftime('%H:%M')
        tensor_df = recent[['T', 'CP', 'VR', 'RSI_14', 'WD', 'PA']].tail(30).round(3)
        
        # 3. Convert to CSV String
        csv_body = tensor_df.to_csv(header=False, index=False).strip()
        header = "T,CP,VR,R,WD,PA"
        
        return f"{header}\n{csv_body}"

if __name__ == "__main__":
    from market_feed import get_live_market_data
    df = get_live_market_data("AAPL")
    processor = RawDataProcessor()
    print(processor.prepare_compressed_tensor(df))
