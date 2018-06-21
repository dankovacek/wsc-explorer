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
                          )
from bokeh.plotting import figure, gmap
from bokeh.palettes import all_palettes
from bokeh.layouts import column, row
from bokeh.events import DoubleTap
from bokeh.models.widgets import (Div,
                                  PreText,
                                  TextInput,
                                  DataTable,
                                  TableColumn,
                                  DateFormatter
                                  )

from modules.base import BaseModule

import os
import json
import logging
import pandas as pd
from stations import IDS_TO_NAMES, IDS_AND_COORDS, STATIONS_DF
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

        columns = [
            TableColumn(field='Station Number', title="Station Number"),
            TableColumn(field='Station Name', title="Station Name"),
            TableColumn(field='distance_to_target',
                        title="Distance from Target [km]"),
            TableColumn(field='Gross Drainage Area (km2)', title='DA [km²]'),
            TableColumn(field='Year From', title="Year From"),
            TableColumn(field='Year To', title="Year To"),
            TableColumn(field='Status', title="Status"),
        ]

        self.station_summary_table = DataTable(
            source=self.nearby_stations_source,
            columns=columns,
            fit_columns=True,
            sortable=True,
            selectable=True,
            width=1200,
            height=200)

        self.search_distance_select = Select(title="Set Search Distance [km]",
                                             value='50', options=['50', '100', '150'])

        self.search_parameter_text = Div(text="""
        <p>1. Use the map or enter project location coordinates to retrieve all the WSC hydrometric stations within
        the distance specified in the `Set Search Distance` dropdown. </p>
        """, width=300, height=80)

        self.station_summary_text = Div(text="""
        <p>2. From the station summary table below (Table 1), select the stations you want to run the analysis on. </p>
        <p><strong>Table 1: Regional WSC Station Summary</strong></p>
        """, width=800, height=30)

    def fetch_data(self, search_distance):
        # Based on the current map location (red dot)
        # find all WSC stations within the specified
        # search distance (dropdown)
        lat = self.current_location_source.data['lat'][0]
        lng = self.current_location_source.data['lng'][0]
        stations_df = get_stations_by_distance(lat, lng, search_distance)

        results = {'nearby_stations': stations_df,
                   'current_location_coords': {'lat': lat, 'lng': lng}
                   }

        return results

        # [START make_plot]

    def make_plot(self, data):
        hover_tool = HoverTool(tooltips=[
            ("Station", "@target_station"),
        ])

        dataframe = data['nearby_stations']

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
                         map_options=map_options, width=900, height=400)

        self.plot.circle(x="Longitude", y="Latitude", size=15,
                         fill_color="blue", fill_alpha=0.8,
                         source=self.nearby_stations_source,
                         # set visual properties for selected glyphs
                         selection_color="orange",
                         nonselection_fill_alpha=0.6,
                         legend="WSC Stations"
                         )

        self.plot.inverted_triangle(x="lng", y="lat", size=11,
                                    fill_color="red", fill_alpha=0.8,
                                    source=self.current_location_source,
                                    legend='Target Location')

        self.title = Div(text="", width=500)

        self.station_select_warning = PreText(text="")

        return column(row(self.plot,
                          column(self.search_parameter_text,
                                 self.lat_input,
                                 self.lng_input,
                                 self.search_distance_select,
                                 )
                          ),
                      row(self.station_summary_text),
                      row(self.station_summary_table)
                      )
# [END make_plot]

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
        print(lat, lng)
        print('######')
        self.current_location_source.data = {'lat': [lat], 'lng': [lng]}

    def initialize_coordinate_inputs(self, lat, lng):
        self.lat_input.value = str(round(lat, 3))
        self.lng_input.value = str(round(lng, 3))

    def update_selected_stations(self, stations):
        if len(stations) >= 2:
            print('selecting first two stations')
            self.nearby_stations_source.selected['1d'].indices = [0, 1]

    def update_nearby_stations(self, data):
        self.nearby_stations_source.data.update(data)

    def map_callback(self, event):
        x, y = convert_coords(event.x, event.y)
        self.update_current_location(x, y)

    def update_map(self, data):
        self.nearby_stations_source.data.update(data['nearby_stations'])

    def busy(self):
        self.title.text = 'Updating...'
        self.plot.background_fill_color = "#efefef"

    def unbusy(self):
        self.title.text = TITLE
        self.plot.background_fill_color = "white"
