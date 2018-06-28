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

from bokeh.models import ColumnDataSource, HoverTool, Paragraph
from bokeh.plotting import figure
from bokeh.palettes import all_palettes
from bokeh.layouts import column
from bokeh.models.widgets import (Div,
                                  PreText,
                                  TextInput,
                                  DataTable,
                                  TableColumn,
                                  DateFormatter
                                  )

from modules.base import BaseModule

from utils import run_query
from stations import IDS_TO_NAMES
import pandas as pd
from get_station_data import get_stations_by_distance

TITLE = 'Unit Area Hydrograph'
TOOLS = "pan,wheel_zoom,box_select,lasso_select,reset,box_zoom"


class Module(BaseModule):

    def __init__(self):
        super().__init__()
        self.source = ColumnDataSource(data={})
        self.found_wsc_stations_source = ColumnDataSource(data=dict())
        self.plot = None
        self.title = Div(text='')

        columns = [
            TableColumn(field='Station Number', title="Station Number"),
            TableColumn(field='Station Name', title="Station Name"),
            TableColumn(field='distance_to_target',
                        title="Distance from Target [km]"),
            TableColumn(field='Gross Drainage Area (km2)', title='DA [km²]'),
            TableColumn(field='Regulation', title='Regulation'),
            TableColumn(field='Year From', title="Year From"),
            TableColumn(field='Year To', title="Year To"),
            TableColumn(field='Status', title="Status"),
        ]

        self.station_summary_table = DataTable(
            source=self.found_wsc_stations_source,
            columns=columns,
            fit_columns=True,
            sortable=True,
            selectable=True,
            width=1200,
            height=200)

        self.station_summary_text = Div(text="""
        <p>2. From the station summary table below (Table 1), select the stations you want to run the analysis on. </p>
        <p><strong>Table 1: Regional WSC Station Summary</strong></p>
        """, width=800, height=30)

    def fetch_wsc_data(self, station):
        return run_query(
            station,
            cache_key=('hydrograph-%s' % station)
        )

# [START make_plot]
    def make_plot_and_table(self, dataframe):
        palette = all_palettes['Spectral'][11]

        self.plot = figure(name='hydrograph',
                           plot_width=1200, plot_height=300, tools=TOOLS,
                           toolbar_location='right', x_axis_type="datetime",
                           title='Figure 2: Concurrent Hydrograph of Daily Unit Runoff [L/s/km²]')

        UR_headings = [e for e in dataframe.columns.values if 'DAILY_UR' in e]

        dataframe['tooltip_date'] = [x.strftime(
            "%Y-%m-%d") for x in dataframe.index]

        dataframe.reset_index(inplace=True)

        self.source.data = self.source.from_df(dataframe)

        tooltips = [("Date", "@tooltip_date")]

        for i, label in enumerate(UR_headings):

            tooltips.append(
                ("{}".format(label), "@{} [L/s/km²]".format(label, label)))

            self.plot.line(
                x='DATE', y=label, source=self.source, line_width=2,
                line_alpha=0.6, line_color=palette[i], legend="{}".format(IDS_TO_NAMES[label[9:]]))

        hover_tool = HoverTool(tooltips=tooltips)
        self.plot.add_tools(hover_tool)
        self.plot.legend.click_policy = "hide"

        return column(self.station_summary_text, self.station_summary_table, self.title, self.plot)

# [END make_plot]
    def get_all_data(self, data_dict):
        return pd.concat([data_dict[e] for e in data_dict], axis=1, join='outer')

    def initialize_selected_wsc_stations(self, stations):
        # set initial selected stations as an example
        self.found_wsc_stations_source.selected['1d'].indices = [0, 1]

    def update_selected_wsc_stations(self, indices):
        self.found_wsc_stations_source.selected['1d'].indices = indices

    def update_found_wsc_stations(self, data):
        self.found_wsc_stations_source.data.update(data)

    def busy(self):
        self.title.text = '<p style="color:red;">Updating...</p>'
        self.plot.background_fill_color = "#efefef"

    def unbusy(self, timer_text):
        self.title.text = timer_text
        self.plot.background_fill_color = "white"
