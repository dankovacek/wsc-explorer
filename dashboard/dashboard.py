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


import logging
import concurrent
import time
import json
import os
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import column, row
from bokeh.models import Select, Paragraph, GMapOptions, ColumnDataSource, MultiSelect
from bokeh.models.widgets import AutocompleteInput, Div, PreText, Button
from bokeh.plotting import gmap
from bokeh.events import DoubleTap
from bokeh.models.formatters import DatetimeTickFormatter

import modules.hydrograph
import modules.map

# import modules.temperature
# import modules.population
# import modules.precipitation
from stations import IDS_TO_NAMES, NAMES_TO_IDS, IDS_AND_COORDS
from get_station_data import get_stations_by_distance

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Hide some noisy warnings
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

# , modules.temperature.Module(), modules.population.Module(), modules.precipitation.Module()]
modules = [modules.hydrograph.Module(), modules.map.Module()]

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


def update(attrname, old, new):
    timer.text = '(Executing %s queries...)' % len(modules)
    for module in modules:
        getattr(module, 'busy')()

    results = fetch_data(NAMES_TO_IDS[new.split(':')[1].strip()])

    for module in modules:
        getattr(module, 'update_plot')(results[module.id])

    for module in modules:
        getattr(module, 'unbusy')()


def station_input_callback(attrname, old, new):
    '''
    When station input is entered, get corresponding
    lat/lon and send to update the neighbouring
    station options.
    '''
    new_station = new.split(':')[0]
    lat, lon = IDS_AND_COORDS[new_station]

    station_input_widget.value = IDS_TO_NAMES[new_station]
    selected_station_text.text = "Selected WSC Station: {}".format(
        IDS_TO_NAMES[new_station])

    update_station_options(lat, lon)


def update_station_options(lat, lon):
    '''
    When the current project location changes,
    update the list of neighbouring stations
    within the specified search distance.
    '''
    stations_within_search_distance = get_stations_by_distance(
        lat, lon, int(search_distance_select.value))[['Station Number']]

    found_stations = [IDS_TO_NAMES[e]
                      for e in stations_within_search_distance['Station Number'].values]
    stations = {'stations': found_stations}
    station_options_source.data = stations


station_id = '08MG005'

current_lat, current_lon = IDS_AND_COORDS[station_id]

station_options_source = ColumnDataSource(
    data=dict(stations=[]))

station_input_widget = AutocompleteInput(value="{}".format(IDS_TO_NAMES[station_id]),
                                         completions=[IDS_TO_NAMES[e]
                                                      for e in IDS_TO_NAMES.keys()],
                                         title='Find Primary Station (use all-caps for autocomplete)',
                                         width=600)

station_input_widget.on_change('value', station_input_callback)

search_distance_select = Select(title="Set Search Distance",
                                value='50', options=['50', '100', '150'])

search_distance_select.on_change('value', update)

station_comparison_options = update_station_options(current_lat, current_lon)

station_select = MultiSelect(title='Select a station:',
                             value=[station_id],
                             options=list(station_options_source.data['stations']))

station_select.on_change('value', update)

selected_station_text = PreText(
    text="Target WSC Station: {}".format(IDS_TO_NAMES[station_id]), width=800)

timer = Paragraph()

results = fetch_data(station_id)

blocks = {}
for module in modules:
    block = getattr(module, 'make_plot')(results[module.id])
    blocks[module.id] = block
print('')
main_title_div = Div(text="""
<h2>WSC Data Historical Data Explorer</h2>
""", width=800, height=30)


curdoc().add_root(
    column(
        row(main_title_div),
        row(station_input_widget, search_distance_select),
        row(selected_station_text),
        row(station_select, timer),
        row(
            column(blocks['modules.map'], blocks['modules.hydrograph']),
            # column(blocks['modules.precipitation'], blocks['modules.population']),
        )
    )
)
curdoc().title = "WSC Explorer: A DKHydrotech Application"
