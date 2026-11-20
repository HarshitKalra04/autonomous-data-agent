import matplotlib
matplotlib.use('Agg')
DATA_PATH = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\sample_data\\sales.csv'
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\charts'
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv(DATA_PATH)
df['marketing_spend'] = df['marketing_spend'].fillna(df['marketing_spend'].median())
df_filtered = df[df['units_sold'] <= 500].copy()

plt.figure(figsize=(10, 6))
plt.scatter(df_filtered['marketing_spend'], df_filtered['units_sold'], alpha=0.5)
plt.xlabel('Marketing Spend')
plt.ylabel('Units Sold')
plt.title('Units Sold vs Marketing Spend (Filtered)')
plt.savefig(f"{CHARTS_DIR}/filtered_marketing.png", dpi=120, bbox_inches="tight")
plt.close()

plt.figure(figsize=(10, 6))
plt.scatter(df_filtered['discount_pct'], df_filtered['units_sold'], alpha=0.5)
plt.xlabel('Discount %')
plt.ylabel('Units Sold')
plt.title('Units Sold vs Discount % (Filtered)')
plt.savefig(f"{CHARTS_DIR}/filtered_discount.png", dpi=120, bbox_inches="tight")
plt.close()
