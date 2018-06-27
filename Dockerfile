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

FROM python:3.6.1

WORKDIR /usr/src/app

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY db/ db/
COPY dashboard/ dashboard/

EXPOSE 5006

# [START CMD]
CMD bokeh serve --disable-index-redirect --num-procs=4 --port=5006 --address=0.0.0.0 --allow-websocket-origin=130.211.36.215.xip.io dashboard/dashboard.py
# [END CMD]
