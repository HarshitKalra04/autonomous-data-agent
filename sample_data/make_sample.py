"""Generates sample_data/sales.csv (synthetic, with a few deliberate data-quality problems)."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 600
region = rng.choice(["North", "South", "East", "West"], n)
price = rng.normal(50, 8, n).round(2)
discount = rng.choice([0, 5, 10, 20], n, p=[0.4, 0.3, 0.2, 0.1])
marketing = rng.gamma(4, 500, n).round(0)
region_boost = pd.Series(region).map({"North": 1.0, "South": 0.85, "East": 1.15, "West": 1.0}).values
units = (200 - 2.2 * price + 3.0 * discount + 0.02 * marketing) * region_boost + rng.normal(0, 12, n)
df = pd.DataFrame({
    "date": pd.date_range("2025-01-01", periods=n, freq="D").strftime("%Y-%m-%d"),
    "region": region, "price": price, "discount_pct": discount,
    "marketing_spend": marketing, "units_sold": units.round(0),
})
df.loc[rng.choice(n, 25, replace=False), "marketing_spend"] = np.nan   # missing values
df.loc[rng.choice(n, 3, replace=False), "units_sold"] = 5000           # outliers
df.to_csv("sample_data/sales.csv", index=False)
print("wrote sample_data/sales.csv", df.shape)
