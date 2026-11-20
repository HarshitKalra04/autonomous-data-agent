import matplotlib
matplotlib.use('Agg')
DATA_PATH = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\sample_data\\sales.csv'
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\charts'
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

df = pd.read_csv(DATA_PATH)
df['marketing_spend'] = df['marketing_spend'].fillna(df['marketing_spend'].median())

# Check correlations
corr_matrix = df.select_dtypes(include=[np.number]).corr()
print("Correlation with units_sold:")
print(corr_matrix['units_sold'].sort_values(ascending=False))

# Identify potential outliers
plt.scatter(df['marketing_spend'], df['units_sold'])
plt.xlabel('Marketing Spend')
plt.ylabel('Units Sold')
plt.savefig(f"{CHARTS_DIR}/marketing_vs_units.png", dpi=120, bbox_inches="tight")
plt.close()

plt.scatter(df['price'], df['units_sold'])
plt.xlabel('Price')
plt.ylabel('Units Sold')
plt.savefig(f"{CHARTS_DIR}/price_vs_units.png", dpi=120, bbox_inches="tight")
plt.close()
