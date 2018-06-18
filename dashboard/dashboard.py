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
from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import (ColumnDataSource, GMapOptions, MultiSelect,
                          Paragraph, Select)
from bokeh.models.formatters import DatetimeTickFormatter
from bokeh.models.widgets import Button, Div, PreText, TextInput
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

modules = [modules.hydrograph.Module(), modules.stationmap.Module()]
# [START fetch_data]


def fetch_data(station):
    """
    Fetch data from WSC for the given station by running
    # the queries for all dashboard modules in parallel.
    """
    t0 = time.time()
    # Collect fetch methods for all dashboard modules
    fetch_methods = {module.id: getattr(
        module, 'fetch_data') for module in modules}
    # Create a thread pool: one separate thread for each dashboard module
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(fetch_methods)) as executor:
        # Prepare the thread tasks
        tasks = {}
        for key, fetch_method in fetch_methods.items():
            print('')
            print('')
            print('')
            print(key, fetch_method)
            print('')
            print('')
            task = executor.submit(fetch_method, station)
            tasks[task] = key
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


def make_query_object():
    return {'lat': lat_input.value,
            'lng': lng_input.value,
            'search_distance': search_distance_select.value,
            'selected_stations': station_select.value}


def update(attrname, old, new):
    timer.text = '(Executing %s queries...)' % len(modules)
    for module in modules:
        getattr(module, 'busy')()

    results = fetch_data(make_query_object())

    for module in modules:
        getattr(module, 'update_plot')(results[module.id])

    for module in modules:
        getattr(module, 'unbusy')()


def update_station_options():
    '''
    When the current project location changes,
    update the list of neighbouring stations
    within the specified search distance.
    '''
    return get_stations_by_distance(
        float(lat_input.value), float(lng_input.value),
        int(search_distance_select.value)).sort_values(by='distance_to_target')


def station_options_callback(attrname, old, new):
    update_station_options()


def update_lat(attrname, old, new):
    if new.isnumeric() and new > -90 and new < 90:
        update(attrname, old, new)
    else:
        lat_input.value = "Enter a value between -90 and 90."


def update_lng(attrname, old, new):
    if new.isnumeric() and new > -180 and new < 180:
        update(attrname, old, new)
    else:
        lng_input.value = "Enter a value between -180 and 180."

# UI Start


station_options_source = ColumnDataSource(
    data=dict(stations=[]))

initial_station_id = '08MG005'

current_lat, current_lng = IDS_AND_COORDS[initial_station_id]

lat_input = TextInput(title="Latitude (dec. degrees)",
                      value=str(current_lat))

lng_input = TextInput(title="Longitude (dec. degrees)",
                      value=str(current_lng))

lat_input.on_change('value', update_lat)
lng_input.on_change('value', update_lng)

search_distance_select = Select(title="Set Search Distance [km]",
                                value='50', options=['50', '100', '150'])

search_distance_select.on_change('value', update)

station_comparison_options = update_station_options()

station_select = MultiSelect(title='Select WSC stations to compare:',
                             value=[IDS_TO_NAMES[initial_station_id]],
                             size=10,
                             options=list(station_options_source.data['stations']))

station_select.on_change('value', station_options_callback)

timer = Paragraph()

results = fetch_data(make_query_object())

blocks = {}
for module in modules:
    block = getattr(module, 'make_plot')(results[module.id])
    blocks[module.id] = block

main_title_div = Div(text="""
<h2>WSC Data Historical Data Explorer</h2>
""", width=800, height=30)


curdoc().add_root(
    column(
        row(main_title_div, timer),
        # row(selected_station_text),
        # row(timer),
        row(blocks['modules.stationmap'],
            column(lat_input, lng_input, search_distance_select, station_select)),
        row(blocks['modules.hydrograph'],
            # column(blocks['modules.precipitation'],
            # blocks['modules.population']),
            )
    )
)
curdoc().title = "WSC Explorer: A DKHydrotech Application"
