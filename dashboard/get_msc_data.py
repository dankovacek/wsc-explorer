import os

import numpy as np
import pandas as pd
import math
import os
import sys
import time
import utm
import time

from multiprocessing import Process, Queue, Pool

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data/')


def load_data(filename):
    fname = os.path.join(DATA_DIR, filename)
    data = pd.read_csv(fname, header=3)

    data['Latitude (Decimal Degrees)'].dropna(inplace=True)
    data['Longitude (Decimal Degrees)'].dropna(inplace=True)

    data['Latitude (Decimal Degrees)'] = data['Latitude (Decimal Degrees)'].astype(
        float)
    data['Longitude (Decimal Degrees)'] = data['Longitude (Decimal Degrees)'].astype(
        float)

    data['dec_deg_latlon'] = data[[
        'Latitude (Decimal Degrees)', 'Longitude (Decimal Degrees)']].values.tolist()

    # convert decimal degrees to utm and make new columns for UTM Northing and Easting
    data['utm_latlon'] = [utm.from_latlon(
        e[0], e[1]) for e in data['dec_deg_latlon']]

    data['utm_E'] = [e[0] for e in data['utm_latlon']]
    data['utm_N'] = [e[1] for e in data['utm_latlon']]

    return data


stn_df = load_data('MSC_Station_Inventory_EN.csv')

# multithreading and queuing inspired from:
# https://stackoverflow.com/questions/36460096/python-multiprocessing-queue-object-has-no-attribute-task-done-join
# user: nneonneo


def web_query(ec_url):
    print('querying url: {}'.format(ec_url))
    df = pd.DataFrame()
    try:
        df = pd.read_csv(ec_url, header=22, parse_dates=['Date/Time'])
    except Exception:
        print('No result returned for requested timeframe.')
    return df


def get_urls_list(station_ID, start_year, end_year, month, t_frame):
    # creates a list containing unique urls for each year or month
    # for hourly, need to add '&Day={}' back in following '&month={}'
    # if interval is daily (1), month is irrelevant
    urls = []
    years = [e for e in range(int(start_year), int(end_year) + 1)]
    ec_base_url = "http://climate.weather.gc.ca/climate_data/bulk_data_e.html?"
    for year in years:
        urls += [ec_base_url + 'format=csv&stationID={}&Year={}&Month={}&Day=14&timeframe={}&submit=Download+Data'.format(
            station_ID, year, 1, t_frame)]
    return urls


def crawl(q, result, index):
    # Keep everything in try/catch loop so we handle errors
    while not q.empty():
        work = q.get()
        try:
            data = pd.read_csv(ec_url, header=22, parse_dates=['Date/Time'])
            print("Requested... " + work[1])
            result[work[0]] = data
        except:
            logging.error('Error with URL check!')
            result[work[0]] = pd.DataFrame()
        q.task_done()
    return True


def make_dataframe(station_ID, start_year, end_year):

    start_time = time.time()

    t_frame = 2  # 2 corresponds to daily, 1 to hourly, 3 to monthly

    # get the station name
    stn_name = str(stn_df[stn_df['Station ID'] == int(station_ID)].Name.item())

    # create a list of urls to query
    url_list = get_urls_list(station_ID, start_year, end_year, 1, t_frame)

    # initialisation for query queuing
    proc = []
    frames = []
    # initialize the queue for storing threads
    p = Pool()

    # store results in a list until all requests complete
    # before concatenating
    results = p.map(web_query, url_list)
    p.close()
    p.join()

    request_time = time.time()
    print('All requests completed in t={}s.'.format(request_time - start_time))

    # initialize a results dataframe
    all_data = pd.DataFrame()
    all_data = pd.concat(results)

    name_col = [stn_name for e in range(len(all_data.index))]

    all_data.insert(0, 'Station Name', np.array(name_col))

    # create unique filename for output file
    t = time.strftime("%d%b%Y_%H%M%S", time.gmtime())
    filename = station_ID + '_' + start_year + '_to_' + end_year + '_' + t + '.csv'

    print('Time to concatenate all data: {}'.format(time.time() - request_time))

    return all_data, filename


def get_stations(lat, lon, radius):
    # input target location decimal degrees [lat, lon]
    target_loc = utm.from_latlon(lat, lon)
    # squamish_utm_loc = utm.from_latlon(49.796, -123.203)

    target_zone = str(target_loc[-2]) + str(target_loc[-1])

    stn_df['distance_to_target'] = np.sqrt((stn_df['utm_E'] - target_loc[0])**2 +
                                           (stn_df['utm_N'] - target_loc[1])**2)

    # enter the distance from the target to search for stations
    search_radius = radius * 1000
    target_stns = stn_df[stn_df['distance_to_target'] <= search_radius]
    target_stns = target_stns.dropna(axis=0, how='any', subset=[
        'MLY First Year', 'MLY Last Year', 'distance_to_target'])

    # filter out results in different utm zones
    target_stns['UTM_Zone'] = [str(e[-2]) + str(e[-1])
                               for e in target_stns['utm_latlon']]

    results = []

    try:
        target_stns = target_stns[target_stns['UTM_Zone'] == target_zone]
    except TypeError as e:
        return results

    for index, row in target_stns.iterrows():
        rec_start = int(row['First Year'])
        rec_end = int(row['Last Year'])
        years = [e for e in range(rec_start, rec_end + 1)]

        stn_latlon = str(stn_df[stn_df['Station ID'] ==
                                row['Station ID']].dec_deg_latlon.item())

        stn_distance_to_target = stn_df[stn_df['Station ID'] ==
                                        row['Station ID']].distance_to_target.astype(float) / 1000

        stn_name = str(stn_df[stn_df['Station ID'] ==
                              row['Station ID']].Name.item())

        # put all results into a dict object to pass to the view
        # don't download unless user requests download
        station = {}

        stn_id = str(row['Station ID']).strip()

        new_file_name = os.path.join(DATA_DIR, stn_name + '_' +
                                     stn_id + '_ID' +
                                     str(rec_start) + '_to_' + str(rec_end) + '.csv')

        # update results dict object with desired parameters
        station['start_year'] = str(rec_start)
        station['end_year'] = str(rec_end)
        station['latlon'] = stn_latlon
        station['distance_to_target'] = stn_distance_to_target
        station['station_name'] = stn_name
        station['station_ID'] = stn_id
        station['new_file_name'] = new_file_name
        results += [station]

    return results
