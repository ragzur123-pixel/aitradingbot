## 2025-02-18 - Replacing Loop-based Wilder's Smoothing with pandas.ewm
**Learning:** Calculating Wilder's Smoothing recursively via Python `for` loops and `pandas.Series.iloc` updates is extremely slow (O(n) overhead). However, `pandas.DataFrame.ewm(alpha=1/period, adjust=False)` perfectly maps to the recursive formula mathematically, offering orders of magnitude speedup via C-level execution.
**Action:** Always prefer `pandas` built-in vectorized functions like `ewm` over iterating through rows with `for` loops, especially when dealing with EMA/SMMA style indicators. Also, always remember to add boundary checks (e.g. `len(series) < period`) when slicing/indexing inside vectorized functions, to prevent regression `IndexError` on short input dataframes!

<<<<<<< HEAD
## 2025-03-09 - Pandas Element-wise Extremum Performance Bottleneck
**Learning:** Using `pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)` to compute element-wise extremums across multiple Series is extremely slow due to the overhead of allocating new DataFrames and executing row-wise `.max()` operations.
**Action:** Always prefer using `np.fmax()` (and `np.fmin()`) over `pd.concat().max(axis=1)` for computing extremums between multiple Series. `np.fmax` handles missing values identically to Pandas' `.max(axis=1)` but executes orders of magnitude faster (e.g., ~130x speedup for computing the True Range).
=======
## 2025-03-01 - Optimizing Pandas element-wise extremums
**Learning:** Using `pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)` is significantly slower due to concatenation overhead. `np.fmax` and `np.fmin` correctly ignore NaNs matching standard Pandas max/min behavior and are vastly faster.
**Action:** Always prefer `np.fmax` and `np.fmin` for computing element-wise extremums across multiple Series to avoid Pandas concatenation overhead.
>>>>>>> origin/main
