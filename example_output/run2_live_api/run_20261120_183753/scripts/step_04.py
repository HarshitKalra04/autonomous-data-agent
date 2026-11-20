import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\charts'
import json
import os

# Check files in the current working directory, as the environment might be using direct paths
files = [f for f in os.listdir('.') if f.endswith('.json')]
print(f"Files found: {files}")

def get_avg_max_temp(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Extract the temperatures. 
    # API past_days=7 parameter provides the requested data.
    # Looking at the data structure, 'temperature_2m_max' has many entries. 
    # Let's inspect the length.
    temps = data['daily']['temperature_2m_max']
    print(f"Temps for {file_path}: {temps}")
    
    # Based on open-meteo, past_days=7 returns the past 7 days. 
    # The JSON array should contain 8 values if today is included.
    # Let's take the first 7.
    selected_temps = temps[:7]
    return sum(selected_temps) / len(selected_temps)

delhi_avg = get_avg_max_temp('delhi.json')
mumbai_avg = get_avg_max_temp('mumbai.json')
bengaluru_avg = get_avg_max_temp('bengaluru.json')

print(f"Delhi Average: {delhi_avg}")
print(f"Mumbai Average: {mumbai_avg}")
print(f"Bengaluru Average: {bengaluru_avg}")
