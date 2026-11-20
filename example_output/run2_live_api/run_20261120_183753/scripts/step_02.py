import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\charts'
import json
import pandas as pd
import os

def get_avg_max_temp(file_path):
    with open(os.path.join('DATA_DIR', file_path), 'r') as f:
        data = json.load(f)
    
    # Extract the last 7 days from the list.
    # The API output has indices 0 to 6 as the past 7 days (the response seems to include a forecast for the next 7 days too).
    # Based on the preview:
    # "daily": {"time": ["2026-11-13", ..., "2026-11-20" (today)], ...}
    # index 0 to 7 represents the past 8 days. Let's take the last 7 entries before today (index 0 to 6).
    
    temps = data['daily']['temperature_2m_max'][:7]
    return sum(temps) / len(temps)

delhi_avg = get_avg_max_temp('delhi.json')
mumbai_avg = get_avg_max_temp('mumbai.json')
bengaluru_avg = get_avg_max_temp('bengaluru.json')

print(f"Delhi Average: {delhi_avg}")
print(f"Mumbai Average: {mumbai_avg}")
print(f"Bengaluru Average: {bengaluru_avg}")
