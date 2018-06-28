# Copyright Google Inc. 2017
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import concurrent
import logging
import os
import time

import pandas as pd
from bokeh.events import DoubleTap
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (ColumnDataSource, GMapOptions, MultiSelect,
                          Paragraph, Select)
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models.widgets import Div, Button, PreText, TextInput
from bokeh.plotting import gmap

import modules.wscModule
import modules.mapModule
# import modules.precipitation
# import modules.temperature

from get_station_data import get_stations_by_distance

from stations import IDS_AND_COORDS, IDS_TO_NAMES, NAMES_TO_IDS


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Hide some noisy warnings
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.WARNING)

map_module = modules.mapModule.Module()
wsc_module = modules.wscModule.Module()
# wsc_table_module = modules.WSC_Table.Module()
modules = [map_module, wsc_module]

# [START fetch_data]


def wsc_data_query(stations):
    """
    Fetch data from WSC for the given stations by running
    # the database/web queries in parallel.
    """
    t0 = time.time()
    # Collect fetch methods for all dashboard modules
    # fetch_method = {module.id: getattr(
    #     module, 'fetch_data') for module in modules}

    # Create a thread pool: one separate thread for each station to be queried
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(stations)) as executor:
        # Prepare the thread tasks
        tasks = {}
        for station in stations:
            task = executor.submit(
                getattr(wsc_module, 'fetch_wsc_data'), station)
            tasks[task] = station
        # Run the tasks and collect results as they arrive
        results = {}
        for task in concurrent.futures.as_completed(tasks):
            key = tasks[task]
            results[key] = task.result()
    # Return results once all tasks have been completed
    t1 = time.time()
    timer.text = '(Executed queries in %s seconds)' % round(t1 - t0, 2)

    return getattr(wsc_module, 'get_all_data')(results)
# [END fetch_data]


def update_map_and_tables(attrname, old, new):
    getattr(map_module, 'busy')()
    # update the source for the map station points
    getattr(map_module, 'find_nearest_wsc_stations')()
    # update the station summary table
    # getattr(wsc_module, 'update_found_wsc_stations')(
    #     getattr(map_module, 'found_wsc_stations_source').data)

    getattr(map_module, 'unbusy')()


def update_wsc_module(attrname, old, new):
    timer.text = '(Executing queries...)'
    getattr(wsc_module, 'busy')()

    # avoid cluttering the UI by limiting simultaneous
    # queries to ten
    if len(new.indices) > 10:
        getattr(map_module, 'unbusy')(
            '<p style="color:red;">Select a maximum of 10 stations.</p>')
        getattr(map_module, 'set_location_error_message')(
            'Select a maximum of 10 stations.')
    else:
        stns = list(getattr(
            wsc_module, 'found_wsc_stations_source').data['Station Number'])
        getattr(map_module, 'set_location_error_message')('')

        getattr(map_module, 'update_selected_wsc_stations')(new.indices)
        getattr(wsc_module, 'update_selected_wsc_stations')(new.indices)

        results = wsc_data_query([stns[e] for e in new.indices])
        # in order to add a series to a plot, we need to replace the child
        # containing the hydrograph in the layout object
        layout.children[2] = row(getattr(
            wsc_module, 'make_plot_and_table')(results))

        getattr(wsc_module, 'unbusy')(timer.text)


#############
# UI Start
# set initial location
initial_location = ['08KC001']
current_lat, current_lng = IDS_AND_COORDS[initial_location[0]]
timer = Div()
blocks = {}

#########
# Map Initialization
#########
# set the initial location source in the map module
getattr(map_module, 'update_current_location')(current_lat, current_lng)
# initialize the lat/lon input values with current location
getattr(map_module, 'update_coordinate_inputs')()
# set the data source for plotted station locations
getattr(map_module, 'find_nearest_wsc_stations')()
# instantiate the map and associated UI elements
blocks['modules.mapModule'] = getattr(map_module, 'make_plot')()

##########
# Map module callbacks triggering wide updates.
##########
getattr(map_module, 'search_distance_select').on_change(
    'value', update_map_and_tables)

# if the current location changes, trigger an update to the map function,
# refresh station search, refresh wsc station table and msc station table
getattr(map_module, 'current_location_source').on_change(
    'data', update_map_and_tables)

# have to have a separate callback to update the table source and the map source
# based on the different selection sources
getattr(map_module, 'found_wsc_stations_source').on_change(
    'selected', update_wsc_module)

#########
# WSC Table and Hydrograph module initialization
#########
getattr(wsc_module, 'update_found_wsc_stations')(
    getattr(map_module, 'found_wsc_stations_source').data)
stns = getattr(wsc_module, 'found_wsc_stations_source')
# intially select closest two stations as an example
getattr(wsc_module, 'initialize_selected_wsc_stations')(
    stns.data['Station Number'])
# get indices for which stations are selected and retrieve
# flow series for selected stations
selected_stations = stns.selected['1d'].indices
flow_results = wsc_data_query([list(stns.data['Station Number'])[e]
                               for e in selected_stations])
# instantiate the wsc table and related UI elements
blocks['modules.wscModule'] = getattr(
    wsc_module, 'make_plot_and_table')(flow_results)

#########
# Hydrograph Module Callbacks
#########
getattr(wsc_module, 'found_wsc_stations_source').on_change(
    'selected', update_wsc_module)


#########
# End Module Callbacks
#########

main_title_div = Div(text="""
<h2>WSC Data Historical Data Explorer</h2>
""", width=800, height=30)

layout = column(
    row(main_title_div),
    # row(selected_station_text),
    row(blocks['modules.mapModule'],
        ),
    row(blocks['modules.wscModule'],
        ),
)

curdoc().add_root(layout)
curdoc().title = "WSC Explorer: A DKHydrotech Application"
