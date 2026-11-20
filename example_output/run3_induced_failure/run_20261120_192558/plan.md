## Plan v1
1. Calculate the date range for the past 7 days (2026-11-13 to 2026-11-19).
2. Fetch historical weather data for Delhi (28.6139, 77.2090), Mumbai (19.0760, 72.8777), and Bengaluru (12.9716, 77.5946) for the specified range using Open-Meteo API.
3. Extract the daily maximum temperature for each city from the JSON responses.
4. Calculate the average daily maximum temperature for each city over the 7-day period.
5. Compare the averages, identify the warmest city, and compile the final report.

## Plan v2 (revision: The batch request to Open-Meteo timed out, possibly due to size or API limitations. I will try fetching the data for each city individually.)
1. Fetch historical weather data for Delhi (28.6139, 77.2090) for 2026-11-13 to 2026-11-19.
2. Fetch historical weather data for Mumbai (19.0760, 72.8777) for 2026-11-13 to 2026-11-19.
3. Fetch historical weather data for Bengaluru (12.9716, 77.5946) for 2026-11-13 to 2026-11-19.
4. Extract daily max temperatures, calculate averages, and compare.