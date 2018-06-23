import pandas as pd
import io
import requests

station = '08MG005'
base_url = 'https://wateroffice.ec.gc.ca/search/historical_results_e.html?search_type=station_number&station_number={}&start_year=1850&end_year=2018'.format(
    station)

c = pd.read_csv(base_url)
print(c.head())
