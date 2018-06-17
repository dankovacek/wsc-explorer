import os

import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'dashboard/data/')

stations_df = pd.read_csv(DATA_DIR + 'WSC_Station_Update_Master.csv')

print(len(stations_df))

stations_df.drop_duplicates(subset="Station Name", inplace=True)

stations_df.to_csv('WSC_Stations_Master.csv')
