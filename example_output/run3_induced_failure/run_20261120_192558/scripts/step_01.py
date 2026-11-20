import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_192558\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_192558'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_192558\\charts'
import json
import os

cities = ['delhi', 'mumbai', 'bengaluru']
averages = {}

for city in cities:
    with open(os.path.join('data', f'{city}.json'), 'r') as f:
        data = json.load(f)
        temps = data['daily']['temperature_2m_max']
        avg_temp = sum(temps) / len(temps)
        averages[city] = avg_temp
        print(f"{city.capitalize()}: {temps} -> Average: {avg_temp:.2f}°C")

print(f"Results: {averages}")
