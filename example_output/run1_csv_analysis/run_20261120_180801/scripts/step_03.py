import matplotlib
matplotlib.use('Agg')
DATA_PATH = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\sample_data\\sales.csv'
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\charts'
import pandas as pd
import numpy as np

df = pd.read_csv(DATA_PATH)
df['marketing_spend'] = df['marketing_spend'].fillna(df['marketing_spend'].median())

# Remove outliers from units_sold (value 5000 is extremely high compared to others)
# Let's see how many records are > 500
print(f"Records > 500: {len(df[df['units_sold'] > 500])}")
df_filtered = df[df['units_sold'] <= 500].copy()

df_filtered = pd.get_dummies(df_filtered, columns=['region'], drop_first=True, dtype=int)

# Standardize variables
features = ['price', 'discount_pct', 'marketing_spend', 'region_North', 'region_South', 'region_West']
X = df_filtered[features].values
y = df_filtered['units_sold'].values

# Normalize features
X_std = (X - X.mean(axis=0)) / X.std(axis=0)
y_std = (y - y.mean()) / y.std()

# Regression
coeffs, _, _, _ = np.linalg.lstsq(X_std, y_std, rcond=None)

results = pd.DataFrame({'feature': features, 'coeff': coeffs})
results['abs_coeff'] = results['coeff'].abs()
results = results.sort_values(by='abs_coeff', ascending=False)
print(results)
