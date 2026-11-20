import matplotlib
matplotlib.use('Agg')
DATA_PATH = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\sample_data\\sales.csv'
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_180801\\charts'
import pandas as pd
import numpy as np

df = pd.read_csv(DATA_PATH)

# Impute marketing_spend with median
df['marketing_spend'] = df['marketing_spend'].fillna(df['marketing_spend'].median())

# Create dummy variables for region
df = pd.get_dummies(df, columns=['region'], drop_first=True, dtype=int)

print(df.head())
print(df.isnull().sum())