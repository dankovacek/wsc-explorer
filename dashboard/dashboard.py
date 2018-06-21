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

import modules.hydrograph
import modules.stationmap
# import modules.precipitation
# import modules.temperature

from get_station_data import get_stations_by_distance

from stations import IDS_AND_COORDS, IDS_TO_NAMES, NAMES_TO_IDS


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Hide some noisy warnings
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

map_module = modules.stationmap.Module()
hydrograph_module = modules.hydrograph.Module()
modules = [map_module, hydrograph_module]

# [START fetch_data]


def fetch_data(stations):
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
                getattr(hydrograph_module, 'fetch_data'), station)
            tasks[task] = station
        # Run the tasks and collect results as they arrive
        results = {}
        for task in concurrent.futures.as_completed(tasks):
            key = tasks[task]
            results[key] = task.result()
    # Return results once all tasks have been completed
    t1 = time.time()
    timer.text = '(Execution time: %s seconds)' % round(t1 - t0, 4)
    return results
# [END fetch_data]


def update_map(attrname, old, new):
    getattr(map_module, 'busy')()

    results = getattr(map_module, 'fetch_data')(
        float(getattr(map_module, 'search_distance_select').value))

    getattr(map_module, 'update_map')(results)
    getattr(map_module, 'update_nearby_stations')(results['nearby_stations'])

    getattr(map_module, 'update_selected_stations')(
        results['nearby_stations']['Station Number'].values)

    getattr(map_module, 'unbusy')()


def update_hydrograph(attrname, old, new):
    timer.text = '(Executing {} queries...)'.format('n')
    getattr(hydrograph_module, 'busy')()

    results = fetch_flow_data(new)
    getattr(map_module, 'update_plot')(results)
    getattr(hydrograph_module, 'update_plot')(results)

    getattr(hydrograph_module, 'unbusy')()


#############
# UI Start
# set initial location
initial_location = ['08KC001']
current_lat, current_lng = IDS_AND_COORDS[initial_location[0]]
timer = Paragraph()
blocks = {}

#########
# Initialization and Callbacks for plot interactions
#########
# set initial location
# this sets the initial location source in the map module
getattr(map_module, 'update_current_location')(current_lat, current_lng)
getattr(map_module, 'initialize_coordinate_inputs')(current_lat, current_lng)

map_results = getattr(map_module, 'fetch_data')(
    float(getattr(map_module, 'search_distance_select').value))

getattr(map_module, 'update_nearby_stations')(map_results['nearby_stations'])
blocks['modules.stationmap'] = getattr(map_module, 'make_plot')(map_results)

##########
# Map module callbacks
# the map callback sets the current location source
#########
getattr(map_module, 'plot').on_event(
    DoubleTap, getattr(map_module, 'map_callback'))

getattr(map_module, 'current_location_source').on_change('data', update_map)

getattr(map_module, 'lat_input').on_change(
    'value', getattr(map_module, 'update_lat'))
getattr(map_module, 'lng_input').on_change(
    'value', getattr(map_module, 'update_lng'))

getattr(map_module, 'search_distance_select').on_change('value', update_map)

#########
# Hydrograph module initialization
#########
stns = getattr(map_module, 'nearby_stations_source').data
getattr(map_module, 'update_selected_stations')(
    stns['Station Number'])

selected_stations = getattr(
    map_module, 'nearby_stations_source').selected['1d'].indices

flow_results = fetch_data([list(stns['Station Number'])[e]
                           for e in selected_stations])
blocks['modules.hydrograph'] = getattr(
    hydrograph_module, 'make_plot')(flow_results)

#########
# Hydrograph Module Callbacks
#########
# getattr(map_module, 'nearby_stations_source').on_change(
#     'value', update_hydrograph)


#########
# End Module Callbacks
#########

main_title_div = Div(text="""
<h2>WSC Data Historical Data Explorer</h2>
""", width=800, height=30)


curdoc().add_root(
    column(
        row(main_title_div, timer),
        # row(selected_station_text),
        row(blocks['modules.stationmap'],
            ),
        row(blocks['modules.hydrograph'],
            # column(blocks['modules.precipitation'],
            # blocks['modules.population']),
            ),
    )
)
curdoc().title = "WSC Explorer: A DKHydrotech Application"
