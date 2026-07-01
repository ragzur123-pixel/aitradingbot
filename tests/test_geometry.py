import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add root to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geometry import calculate_swing_points, calculate_fvg, calculate_smt_divergence, check_geometric_distance

class TestGeometry(unittest.TestCase):
    def setUp(self):
        # Create a sample dataframe for testing
        data = {
            'High': [10, 11, 12, 11, 10, 11, 12, 13, 12, 11, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11],
            'Low': [9, 10, 11, 10, 9, 10, 11, 12, 11, 10, 9, 10, 11, 12, 13, 14, 13, 12, 11, 10],
            'Close': [9.5, 10.5, 11.5, 10.5, 9.5, 10.5, 11.5, 12.5, 11.5, 10.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 13.5, 12.5, 11.5, 10.5]
        }
        self.df = pd.DataFrame(data)

    def test_calculate_swing_points(self):
        df_swings = calculate_swing_points(self.df, window=2)
        self.assertIn('swing_high', df_swings.columns)
        self.assertIn('swing_low', df_swings.columns)
        # Check a known swing high at index 2 (H=12, window=2)
        self.assertEqual(df_swings['swing_high'].iloc[2], 12.0)
        # Check a known swing low at index 4 (L=9, window=2)
        self.assertEqual(df_swings['swing_low'].iloc[4], 9.0)

    def test_calculate_fvg(self):
        # Create a gap
        self.df.at[5, 'Low'] = 15
        self.df.at[3, 'High'] = 10
        # Low(5)=15 > High(3)=10 => Bullish FVG
        fvgs = calculate_fvg(self.df)
        self.assertTrue(any(f['type'] == 'BULLISH_FVG' for f in fvgs))

    def test_calculate_smt_divergence(self):
        # Primary: Lower Low
        df_p = self.df.copy()
        df_p.at[19, 'Low'] = 5
        df_p.at[9, 'Low'] = 10
        
        # Correlated: Higher Low
        df_c = self.df.copy()
        df_c.at[19, 'Low'] = 15
        df_c.at[9, 'Low'] = 10
        
        smt = calculate_smt_divergence(df_p, df_c)
        self.assertEqual(smt, "BULLISH_SMT_DIVERGENCE")

    def test_check_geometric_distance(self):
        dist = check_geometric_distance(100.0, 102.5)
        self.assertEqual(dist, 2.5)

if __name__ == "__main__":
    unittest.main()
