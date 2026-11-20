import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_192558\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_192558'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_192558\\charts'
import json
import os
import matplotlib.pyplot as plt

cities = ['delhi', 'mumbai', 'bengaluru']
names = [c.capitalize() for c in cities]
averages = []

for city in cities:
    with open(os.path.join('data', f'{city}.json'), 'r') as f:
        data = json.load(f)
        temps = data['daily']['temperature_2m_max']
        averages.append(sum(temps) / len(temps))

plt.figure(figsize=(8, 5))
plt.bar(names, averages, color=['skyblue', 'orange', 'lightgreen'])
plt.ylabel('Average Daily Max Temp (°C)')
plt.title('Average Max Temperature (Nov 13-19, 2026)')
plt.savefig(f"{'charts'}/city_temps.png", dpi=120, bbox_inches="tight")
print("Chart saved")
