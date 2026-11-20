import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\charts'
import json
import os

# Data files were saved into 'data' directory
data_dir = 'data'
files = os.listdir(data_dir)
print(f"Files found in data: {files}")

def get_avg_max_temp(file_name):
    with open(os.path.join(data_dir, file_name), 'r') as f:
        data = json.load(f)
    
    # Extract the past 7 days temperatures.
    # The API output includes 14 days total: 7 past, today, 6 forecast.
    # We want exactly the last 7 days.
    # The JSON array 'temperature_2m_max' has indices 0 to 6 as the past 7 days.
    temps = data['daily']['temperature_2m_max'][:7]
    return sum(temps) / len(temps)

delhi_avg = get_avg_max_temp('delhi.json')
mumbai_avg = get_avg_max_temp('mumbai.json')
bengaluru_avg = get_avg_max_temp('bengaluru.json')

print(f"Delhi Average: {delhi_avg}")
print(f"Mumbai Average: {mumbai_avg}")
print(f"Bengaluru Average: {bengaluru_avg}")
