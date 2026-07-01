import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add root to path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from indicators import calculate_rsi, calculate_sma, calculate_ema, calculate_donchian, calculate_pivots

class TestIndicators(unittest.TestCase):
    def setUp(self):
        # Create a sample dataframe for testing
        data = {
            'High': [10, 11, 12, 11, 10, 9, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21],
            'Low': [9, 10, 11, 10, 9, 8, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
            'Close': [9.5, 10.5, 11.5, 10.5, 9.5, 8.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5, 19.5, 20.5]
        }
        self.df = pd.DataFrame(data)

    def test_calculate_rsi(self):
        rsi = calculate_rsi(self.df['Close'], period=14)
        self.assertEqual(len(rsi), 20)
        # Check if RSI values are between 0 and 100
        self.assertTrue(all((rsi >= 0) & (rsi <= 100)))
        # Check handling of small data
        small_rsi = calculate_rsi(self.df['Close'][:5], period=14)
        self.assertEqual(list(small_rsi), [50.0] * 5)

    def test_calculate_sma(self):
        sma = calculate_sma(self.df['Close'], period=5)
        self.assertEqual(len(sma), 20)
        self.assertTrue(np.isnan(sma[0]))
        self.assertAlmostEqual(sma[4], 10.3) # (9.5+10.5+11.5+10.5+9.5)/5 = 10.3

    def test_calculate_ema(self):
        ema = calculate_ema(self.df['Close'], period=5)
        self.assertEqual(len(ema), 20)
        self.assertFalse(np.isnan(ema[0])) # EMA usually starts with the first value
        self.assertEqual(ema[0], 9.5)

    def test_calculate_donchian(self):
        lower, upper = calculate_donchian(self.df, period=5)
        self.assertEqual(len(lower), 20)
        self.assertEqual(len(upper), 20)
        self.assertEqual(upper[4], 12.0)
        self.assertEqual(lower[4], 9.0)

    def test_calculate_pivots(self):
        pivots = calculate_pivots(self.df)
        self.assertIsNotNone(pivots)
        self.assertIn("P", pivots)
        self.assertIn("R1", pivots)
        self.assertIn("S1", pivots)
        
        # Last candle in setup is index 19, so previous is index 18
        # H=20, L=19, C=19.5
        # P = (20+19+19.5)/3 = 58.5/3 = 19.5
        self.assertEqual(pivots["P"], 19.5)

if __name__ == "__main__":
    unittest.main()
