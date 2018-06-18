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

from bokeh.models import ColumnDataSource, HoverTool, Paragraph, GMapOptions
from bokeh.plotting import figure, gmap
from bokeh.palettes import all_palettes
from bokeh.layouts import column
from bokeh.events import DoubleTap
from bokeh.models.widgets import Div

from modules.base import BaseModule

import os
import json
import logging
import pandas as pd
from stations import IDS_TO_NAMES, IDS_AND_COORDS
from utils import convert_coords


TITLE = 'Target Location'
TOOLS = "pan,wheel_zoom,box_select,lasso_select,reset,box_zoom"


class Module(BaseModule):

    def __init__(self):
        super().__init__()
        self.nearby_stations_source = ColumnDataSource(data=dict())
        self.target_station_source = ColumnDataSource(data=dict())
        self.plot = None
        self.title = None

    def fetch_data(self, station):
        lat, lng = IDS_AND_COORDS[station]
        results = {'target_station': station,
                   'target_coords': {'lat': lat, 'lng': lng}}

        return results

        # [START make_plot]
    def make_plot(self, data):

        self.target_station_source.data = {'lat': [data['target_coords']['lat']],
                                           'lng': [data['target_coords']['lng']]}

        print(data)
        self.nearby_stations_source.data = {'lat': [],
                                            'lng': []}
        palette = all_palettes['Set2'][6]

        hover_tool = HoverTool(tooltips=[
            ("Station", "@target_station"),
        ])

        map_options = GMapOptions(
            lat=data['target_coords']['lat'],
            lng=data['target_coords']['lng'],
            map_type="hybrid",
            zoom=11)

        BASE_DIR = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

        with open(os.path.join(BASE_DIR, 'api_key/client_secret_548109306400.json')) as f:
            GOOGLE_API_KEY = json.load(f)

        self.plot = gmap(google_api_key=GOOGLE_API_KEY['api_key'],
                         map_options=map_options, width=700, height=450)

        self.plot.circle(x="lng", y="lat", size=15,
                         fill_color="red", fill_alpha=0.8,
                         source=self.target_station_source)

        self.plot.circle(x="lng", y="lat", size=15,
                         fill_color="blue", fill_alpha=0.8,
                         source=self.nearby_stations_source)

        self.plot.on_event(DoubleTap, self.map_callback)

        self.title = Div(text="", width=500)
        return column(self.title, self.plot)
# [END make_plot]

    def map_callback(self, event):
        x, y = convert_coords(event.x, event.y)
        self.target_station_source.data = dict(lat=[y], lng=[x])

    def update_plot(self, dataframe):
        self.target_station_source.update()
        self.nearby_stations_source.update()

    def busy(self):
        self.title.text = 'Updating...'
        self.plot.background_fill_color = "#efefef"

    def unbusy(self):
        self.title.text = TITLE
        self.plot.background_fill_color = "white"
