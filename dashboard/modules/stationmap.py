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

from bokeh.models import (ColumnDataSource,
                          HoverTool,
                          Paragraph,
                          GMapOptions,
                          Select,
                          MultiSelect
                          )
from bokeh.plotting import figure, gmap
from bokeh.palettes import all_palettes
from bokeh.layouts import column, row
from bokeh.events import DoubleTap
from bokeh.models.widgets import Div, PreText, TextInput

from modules.base import BaseModule

import os
import json
import logging
import pandas as pd
from stations import IDS_TO_NAMES, IDS_AND_COORDS
from utils import convert_coords
from get_station_data import get_stations_by_distance


TITLE = 'Target Location'
TOOLS = "pan,wheel_zoom,box_select,lasso_select,reset,box_zoom"


class Module(BaseModule):

    def __init__(self):
        super().__init__()
        self.current_location_source = ColumnDataSource(data=dict())
        self.nearby_stations_source = ColumnDataSource(data=dict())
        self.plot = None
        self.title = None
        # additional UI features

        self.lat_input = TextInput(title="Latitude (dec. degrees)",
                                   value='')

        self.lng_input = TextInput(title="Longitude (dec. degrees)",
                                   value='')

        self.station_select = MultiSelect(
            title='Select WSC stations to compare:',
            value=[],
            size=10,
            options=[]
        )

        self.search_distance_select = Select(title="Set Search Distance [km]",
                                             value='50', options=['50', '100', '150'])

    def fetch_data(self, search_distance):
        # Based on the current map location (red dot)
        # find all WSC stations within the specified
        # search distance (dropdown)
        print('fetch data current location')
        print(self.current_location_source.data)
        lat = self.current_location_source.data['lat'][0]
        lng = self.current_location_source.data['lng'][0]
        stations = list(get_stations_by_distance(lat, lng, search_distance)[
            'Station Number'].values)

        lats = []
        lngs = []

        for station in stations:
            lats.append(IDS_AND_COORDS[station][0])
            lngs.append(IDS_AND_COORDS[station][1])

        results = {'nearby_stations': {'stations': [IDS_TO_NAMES[e] for e in stations],
                                       'lat': lats,
                                       'lng': lngs
                                       },
                   'current_location_coords': {'lat': lat, 'lng': lng}
                   }

        return results

        # [START make_plot]

    def make_plot(self, data):
        hover_tool = HoverTool(tooltips=[
            ("Station", "@target_station"),
        ])

        map_options = GMapOptions(
            lat=data['current_location_coords']['lat'],
            lng=data['current_location_coords']['lng'],
            map_type="hybrid",
            zoom=9
        )

        BASE_DIR = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        with open(os.path.join(BASE_DIR, 'api_key/client_secret_548109306400.json')) as f:
            GOOGLE_API_KEY = json.load(f)

        self.plot = gmap(google_api_key=GOOGLE_API_KEY['api_key'],
                         map_options=map_options, width=700, height=450)

        self.plot.circle(x="lng", y="lat", size=15,
                         fill_color="blue", fill_alpha=0.8,
                         source=self.nearby_stations_source,
                         # set visual properties for selected glyphs
                         selection_color="orange",
                         )

        self.plot.circle(x="lng", y="lat", size=15,
                         fill_color="red", fill_alpha=0.8,
                         source=self.current_location_source)

        self.title = Div(text="", width=500)

        self.station_select_warning = PreText(text="")

        return row(column(self.title, self.plot),
                   column(self.lat_input,
                          self.lng_input,
                          self.search_distance_select,
                          self.station_select),
                   )

# [END make_plot]
    def update_selected_stations(self, attrname, old, new):
        if not new:
            self.station_select_warning.text = "Select stations to compare."
        elif len(new) > 4:
            self.station_select_warning.text = "Select A Maximum 4 Stations."
        elif len(new) < 2:
            self.station_select_warning.text = "Select A Minimum 2 Stations."
        else:
            self.station_select_warning.text = "{} stations selected for comparison."
        pass

    def update_lat(self, attrname, old, new):
        if new.isnumeric() and new > -90 and new < 90:
            self.current_location_source.data = {
                'lat': [new], 'lng': [self.lng_input.value]}
        else:
            self.lat_input.value = "Enter a value between -90 and 90."

    def update_lng(self, attrname, old, new):
        if new.isnumeric() and new > -180 and new < 180:
            self.current_location_source.data = {
                'lat': [self.lat_input.value], 'lng': [new]}
        else:
            self.lng_input.value = "Enter a value between -180 and 180."

    def update_current_location(self, lat, lng):
        self.current_location_source.data = {'lat': [lat], 'lng': [lng]}

    def initialize_coordinate_inputs(self, lat, lng):
        self.lat_input.value = str(round(lat, 3))
        self.lng_input.value = str(round(lng, 3))

    def update_nearby_stations(self, stations):
        print('map module update nearby stations')
        print(stations)
        print('')
        self.nearby_stations_source.data = stations

    def update_station_selection(self, stations):
        self.station_select.options = stations
        self.station_select.value = stations[:2]

    def map_callback(self, event):
        x, y = convert_coords(event.x, event.y)
        self.update_current_location(x, y)

    def update_map(self, data):
        print('map module update map')
        print(data)
        print('')
        self.nearby_stations_source.data = data['nearby_stations']

    def busy(self):
        self.title.text = 'Updating...'
        self.plot.background_fill_color = "#efefef"

    def unbusy(self):
        self.title.text = TITLE
        self.plot.background_fill_color = "white"
