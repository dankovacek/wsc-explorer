import numpy as np
import pandas as pd
import math
import os
import sys
import time
import re
from datetime import date
import utm

import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data/')

from stations import IDS_AND_DAS, STATIONS_DF

day_labels = {}
flag_labels = {}
for i in range(1, 32):
    day_labels['FLOW' + str(i)] = i
    flag_labels['FLOW_SYMBOL' + str(i)] = i


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)

    return None


def get_daily_UR(station, station_da):
    time0 = time.time()
    # create a database connection
    cols = ['STATION_NUMBER', 'YEAR', 'MONTH', 'NO_DAYS']

    cols += day_labels.keys()

    columns = ['YEAR', 'MONTH', 'NO_DAYS']
    conn = create_connection('db/Hydat.sqlite3')

    with conn:
        # print("1. Daily average flow query for station ID {}:".format(station))
        return select_dly_flows_by_station_ID(conn, station, station_da)

    conn.close()


def map_day_to_var_name(s):
    if re.search('\d', s):
        return s[re.search('\d', s).span()[0]:]
    else:
        print('substring not found')


def melt_(df):
    id_vars = df.index.names
    return df.reset_index().melt(id_vars=id_vars).set_index(id_vars)


def select_dly_flows_by_station_ID(conn, station):
    """
    Query tasks by priority
    :param conn: the Connection object
    :param station: station number (ID) according to WSC convention
    :return: dataframe object of daily flows
    """
    time0 = time.time()
    cur = conn.cursor()
    cur.execute("SELECT * FROM DLY_FLOWS WHERE STATION_NUMBER=?", (station,))

    rows = cur.fetchall()

    column_headers = [description[0] for description in cur.description]
    id_var_headers = column_headers[:11]

    df = pd.DataFrame(rows, columns=column_headers)
    df.drop(['MONTHLY_MEAN', 'MONTHLY_TOTAL', 'FIRST_DAY_MIN',
             'MIN', 'FIRST_DAY_MAX', 'MAX'], axis=1, inplace=True)

    timex = time.time()
    all_val_vars = [e for e in column_headers if 'FLOW' in e]
    flag_val_vars = [e for e in all_val_vars if 'FLOW_SYMBOL' in e]
    flow_val_vars = [e for e in all_val_vars if '_' not in e]

    df_flows = pd.melt(df,
                       id_vars=id_var_headers,
                       value_vars=flow_val_vars,
                       value_name='DAILY_FLOW',
                       var_name='DAY').sort_values(by=['YEAR', 'MONTH'])

    df_flows['DAY'] = df_flows['DAY'].apply(
        map_day_to_var_name)

    df_flags = pd.melt(df,
                       id_vars=id_var_headers,
                       value_vars=flag_val_vars,
                       value_name='FLAG',
                       var_name='DAY').sort_values(by=['YEAR', 'MONTH'])

    #print('time to melt = ', time.time() - timex)
    df_flows['FLAG'] = df_flags['FLAG']
    # filter out day row if it's not a day that exists in given month
    df_flows = df_flows[df_flows['DAY'].astype(
        int) <= df_flows['NO_DAYS'].astype(int)].dropna(subset=['DAILY_FLOW'])

    dates = df_flows['YEAR'].astype(
        str) + '-' + df_flows['MONTH'].astype(str) + '-' + df_flows['DAY'].astype(str)
    df_flows['DATE'] = pd.to_datetime(dates, format='%Y-%m-%d')

    out = pd.DataFrame()
    out['DATE'] = df_flows['DATE']
    if IDS_AND_DAS[station] > 0:
        out['DAILY_UR_{}'.format(
            station)] = df_flows['DAILY_FLOW'] / IDS_AND_DAS[station] * 1000
    out['FLAG_{}'.format(station)] = df_flows['FLAG']
    out.set_index('DATE', inplace=True)
    if len(out) > 0:
        return out
    else:
        return None


def get_daily_UR(station):
    time0 = time.time()
    # create a database connection
    cols = ['STATION_NUMBER', 'YEAR', 'MONTH', 'NO_DAYS']

    cols += day_labels.keys()

    columns = ['YEAR', 'MONTH', 'NO_DAYS']
    conn = create_connection('db/Hydat.sqlite3')

    with conn:
        # print("1. Daily average flow query for station ID {}:".format(station))
        return select_dly_flows_by_station_ID(conn, station)

    conn.close()


def get_stations_by_distance(lat, lon, radius):
    # input target location decimal degrees [lat, lon]
    # (search) radius in km
    target_loc = utm.from_latlon(lat, lon)
    # squamish_utm_loc = utm.from_latlon(49.796, -123.203)

    target_zone = str(target_loc[-2]) + str(target_loc[-1])

    STATIONS_DF['distance_to_target'] = np.sqrt((STATIONS_DF['utm_E'] - target_loc[0])**2 +
                                                (STATIONS_DF['utm_N'] - target_loc[1])**2)

    # enter the distance from the target to search for stations
    search_radius = radius * 1000
    target_stns = STATIONS_DF[STATIONS_DF['distance_to_target']
                              <= search_radius]

    # filter out results in different utm zones
    target_stns['UTM_Zone'] = [str(e[-2]) + str(e[-1])
                               for e in target_stns['utm_latlon']]

    try:
        target_stns = target_stns[target_stns['UTM_Zone'] == target_zone]
    except TypeError as e:
        return []

    return target_stns
