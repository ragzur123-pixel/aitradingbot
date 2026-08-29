import pandas as pd
import numpy as np
import time
from indicators import calculate_atr

# Create a large dataframe
n = 1000000
df = pd.DataFrame({
    'High': np.random.rand(n) * 100 + 50,
    'Low': np.random.rand(n) * 100,
    'Close': np.random.rand(n) * 100 + 25
})

# Warm up
tr1 = df['High'] - df['Low']
tr2 = abs(df['High'] - df['Close'].shift())
tr3 = abs(df['Low'] - df['Close'].shift())

start = time.time()
res1 = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
time1 = time.time() - start

start = time.time()
res2 = np.fmax(tr1, np.fmax(tr2, tr3))
time2 = time.time() - start

print(f"pd.concat().max(axis=1) time: {time1:.4f}s")
print(f"np.fmax() time: {time2:.4f}s")
print(f"Speedup: {time1/time2:.2f}x")
print(f"Results match: {np.allclose(res1.fillna(0), res2.fillna(0))}")
