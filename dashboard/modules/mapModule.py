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


TITLE = "Figure 1: Project Location and Regional Station Map"
TOOLS = "pan,wheel_zoom,box_select,reset"


class Module(BaseModule):

    def __init__(self):
        super().__init__()
        self.current_location_source = ColumnDataSource(data=dict())
        self.found_wsc_stations_source = ColumnDataSource(data=dict())
        self.plot = None
        self.title = Div(text="")
        self.coordinate_input_warning = Div(text="", width=300, height=15)
        # additional UI features

        self.lat_input = TextInput(title="Latitude (dec. degrees)",
                                   value='')

        self.lng_input = TextInput(title="Longitude (dec. degrees)",
                                   value='')

        # Callbacks
        self.lat_input.on_change('value', self.update_lat)
        self.lng_input.on_change('value', self.update_lng)

        self.search_distance_select = Select(title="Set Search Distance [km]",
                                             value='50', options=['50', '100', '150'])

        self.search_parameter_text = Div(text="""
        <p>1. Use the map or enter project location coordinates to retrieve all the WSC hydrometric stations within
        the distance specified in the `Set Search Distance` dropdown. </p>
        """, width=300, height=80)

    def update_lat(self, attrname, old, new):
        try:
            if float(new) >= -90 and float(new) <= 90:
                self.update_current_location(
                    float(new), float(self.lng_input.value))
                if self.plot is not None:
                    self.plot.map_options.lat = float(new)
                self.set_location_error_message("")
        except ValueError:
            self.set_location_error_message(
                'Latitude must be between -90 and 90.')

    def update_lng(self, attrname, old, new):
        try:
            if float(new) >= -180 and float(new) <= 180:
                self.update_current_location(
                    float(self.lat_input.value), float(new))
                if self.plot is not None:
                    self.plot.map_options.lng = float(new)
                self.set_location_error_message("")
        except ValueError:
            self.set_location_error_message(
                "Longitude must be between -180 and 180.")

    def find_nearest_wsc_stations(self):
        # Based on the current map location (red dot)
        # find all WSC stations within the specified
        # search distance (dropdown)
        lat = self.current_location_source.data['lat'][0]
        lng = self.current_location_source.data['lng'][0]
        stations_df = get_stations_by_distance(
            lat, lng, float(self.search_distance_select.value))

        self.update_found_wsc_stations(stations_df)

        # [START make_plot]

    def make_plot(self):
        hover_tool = HoverTool(tooltips=[
            ("Station", "@target_station"),
        ])

        dataframe = self.found_wsc_stations_source.data

        current_loc = self.current_location_source.data

        map_options = GMapOptions(
            lat=current_loc['lat'][0],
            lng=current_loc['lng'][0],
            map_type="hybrid",
            zoom=8
        )

        BASE_DIR = os.path.dirname(os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))

        with open('dashboard/api_key/client_secret_548109306400.json') as f:
            GOOGLE_API_KEY = json.load(f)

        self.plot = gmap(google_api_key=GOOGLE_API_KEY['api_key'], name='map',
                         map_options=map_options, width=900, height=400,
                         tools=TOOLS,
                         title=TITLE)

        self.plot.circle(x="Longitude", y="Latitude", size=15,
                         fill_color="blue", fill_alpha=0.8,
                         source=self.found_wsc_stations_source,
                         # set visual properties for selected glyphs
                         selection_color="orange",
                         nonselection_fill_alpha=0.6,
                         legend="WSC Stations"
                         )

        self.plot.inverted_triangle(x="lng", y="lat", size=11,
                                    fill_color="red", fill_alpha=0.8,
                                    source=self.current_location_source,
                                    legend='Target Location')

        self.plot.on_event(DoubleTap, self.map_callback)

        return column(row(self.plot,
                          column(self.search_parameter_text,
                                 self.lat_input,
                                 self.lng_input,
                                 self.coordinate_input_warning,
                                 self.search_distance_select,
                                 )
                          ),
                      )
# [END make_plot]

    def set_location_error_message(self, message):
        self.coordinate_input_warning.text = "<p style='color:red;'>{}</p>".format(
            message)

    def update_current_location(self, lat, lng):
        self.current_location_source.data = {'lat': [lat], 'lng': [lng]}

    def update_selected_wsc_stations(self, indices):
        self.found_wsc_stations_source.selected['1d'].indices = indices

    def update_coordinate_inputs(self):
        self.lat_input.value = str(self.current_location_source.data['lat'][0])
        self.lng_input.value = str(self.current_location_source.data['lng'][0])

    def update_found_wsc_stations(self, data):
        self.found_wsc_stations_source.data.update(data)

    def map_callback(self, event):
        x, y = convert_coords(event.x, event.y)
        self.update_current_location(x, y)
        # clear selections

    def busy(self):
        self.plot.title.text = 'Updating...'
        self.plot.background_fill_color = "#efefef"

    def unbusy(self):
        self.plot.title.text = TITLE
        self.plot.background_fill_color = "white"
