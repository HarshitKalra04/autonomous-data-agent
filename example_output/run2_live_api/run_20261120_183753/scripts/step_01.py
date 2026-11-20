import matplotlib
matplotlib.use('Agg')
DATA_PATH = None
DATA_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\data'
OUTPUT_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753'
CHARTS_DIR = 'C:\\Users\\kalra\\OneDrive\\Desktop\\Projects\\autonomous-data-agent\\outputs\\run_20261120_183753\\charts'
import datetime
# Delhi: 28.6139, 77.2090
# Mumbai: 19.0760, 72.8777
# Bengaluru: 12.9716, 77.5946

today = datetime.date.today()
seven_days_ago = today - datetime.timedelta(days=7)

print(f"Start date: {seven_days_ago}, End date: {today}")
