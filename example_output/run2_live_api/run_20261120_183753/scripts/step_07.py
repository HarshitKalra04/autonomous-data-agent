import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\charts'
import matplotlib.pyplot as plt
import pandas as pd
import os

data_dir = 'data'
cities = ['Delhi', 'Mumbai', 'Bengaluru']
averages = [26.74, 34.00, 28.24]

plt.figure(figsize=(8, 6))
plt.bar(cities, averages, color=['skyblue', 'salmon', 'lightgreen'])
plt.ylabel('Average Max Temp (°C)')
plt.title('Average Daily Max Temp (Past 7 Days)')
plt.savefig(f"charts/temp_comparison.png")
plt.close()
