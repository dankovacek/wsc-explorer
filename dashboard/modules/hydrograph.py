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

from modules.base import BaseModule
import modules.stationmap

from utils import run_query
from stations import IDS_TO_NAMES
import pandas as pd
from get_station_data import get_stations_by_distance


TITLE = 'Daily Hydrograph: Unit Runoff [L/s/km²]'
TOOLS = "pan,wheel_zoom,box_select,lasso_select,reset,box_zoom"

map_module = modules.stationmap.Module()


class Module(BaseModule):

    def __init__(self):
        super().__init__()
        self.source = None
        self.plot = None
        self.title = None
        self.selected_stations = 'tricked you!'

    def fetch_data(self, station):
        return run_query(
            station,
            cache_key=('hydrograph-%s' % station)
        )

# [START make_plot]
    def make_plot(self, data_dict):

        columns = {}

        palette = all_palettes['Spectral'][6]

        self.plot = figure(
            plot_width=1200, plot_height=300, tools=TOOLS,
            toolbar_location=None, x_axis_type="datetime")

        self.title = Paragraph(text=TITLE)

        for station in list(data_dict.keys())[:1]:
            dataframe = data_dict[station]
            print('')
            print('hydrograph module')
            print(dataframe.head())

            station_id = dataframe.columns.values[0].split('DAILY_UR_')[1]

            self.source = ColumnDataSource(data=dataframe)

            dataframe['tooltip_date'] = [x.strftime(
                "%Y-%m-%d") for x in dataframe.index]

            UR_heading = [
                e for e in dataframe.columns.values if 'DAILY_UR' in e][0]

            hover_tool = HoverTool(tooltips=[
                ("Date", "@tooltip_date"),
                ("Unit Runoff", "@{}".format(UR_heading)),
            ])

            self.plot.add_tools(hover_tool)

            columns['{}'.format(UR_heading)] = '{}'.format(station_id)

            for i, (code, label) in enumerate(columns.items()):
                self.plot.line(
                    x='DATE', y=code, source=self.source, line_width=3,
                    line_alpha=0.6, line_color=palette[i], legend=label)

        return column(self.title, self.plot)
# [END make_plot]

    def get_concurrent_data(self, df1, df2):
        df1_id = df1['Station Number'].values[0]
        df2_id = df2['Station Number'].values[0]

        df1_ur = 'DAILY_UR_{}'.format(df1_id)
        df2_ur = 'DAILY_UR_{}'.format(df2_id)

        df1.rename(index=str, columns={
            'DAILY_FLOW': df1_ur, 'FLAG': 'FLAG_{}'.format(df1_id)}, inplace=True)
        df2.rename(index=str, columns={
            'DAILY_FLOW': df2_ur, 'FLAG': 'FLAG_{}'.format(df2_id)}, inplace=True)

        return pd.concat([s1_df, s2_df], axis=1, join='inner')

    def update_plot(self, dataframe):
        self.source.data.update(dataframe)

    def busy(self):
        self.title.text = 'Updating...'
        self.plot.background_fill_color = "#efefef"

    def unbusy(self):
        self.title.text = TITLE
        self.plot.background_fill_color = "white"
