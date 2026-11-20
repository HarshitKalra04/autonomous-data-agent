import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\charts'
import json
import os

# Check files in DATA_DIR
print(os.listdir('DATA_DIR'))

def get_avg_max_temp(file_path):
    with open(os.path.join('DATA_DIR', file_path), 'r') as f:
        data = json.load(f)
    
    # The API returns past_days=7. Let's look at the 'time' array length.
    # The 'daily' data contains the requested days.
    temps = data['daily']['temperature_2m_max'][:7]
    return sum(temps) / len(temps)

delhi_avg = get_avg_max_temp('delhi.json')
mumbai_avg = get_avg_max_temp('mumbai.json')
bengaluru_avg = get_avg_max_temp('bengaluru.json')

print(f"Delhi Average: {delhi_avg}")
print(f"Mumbai Average: {mumbai_avg}")
print(f"Bengaluru Average: {bengaluru_avg}")
