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


import json
import os
import socket
from datetime import datetime

import pandas as pd
from pymemcache.client.hash import HashClient
from pyproj import Proj, transform

from get_station_data import get_daily_UR, get_stations_by_distance


class MemcachedDiscovery:

    def __init__(self, host='memcached.default.svc.cluster.local', port=11211, resync_interval=10):
        self._client = None
        self._t0 = None
        self._ips = []
        self.resync_interval = resync_interval
        self.host = host
        self.port = port

    def _resync(self):
        """
        Check if the list of available nodes has changed. If any change is
        detected, a new HashClient pointing to all currently available
        nodes is returned, otherwise the current client is returned.
        """
        # Collect the all Memcached pods' IP addresses
        try:
            _, _, ips = socket.gethostbyname_ex(self.host)
        except socket.gaierror:
            # The host could not be found. This mean that either the service is
            # down or that no pods are running
            ips = []
        if set(ips) != set(self._ips):
            # A different list of ips has been detected, so we generate
            # a new client
            self._ips = ips
            if self._ips:
                servers = [(ip, self.port) for ip in self._ips]
                self._client = HashClient(servers, use_pooling=True)
            else:
                self._client = None

    def get_client(self):
        # Check if we are due for a resync of Memcached nodes
        now = datetime.now()
        due_for_resync = self._t0 is None or (
            now - self._t0).total_seconds() > self.resync_interval
        if due_for_resync:
            # Request a resync
            self._resync()
            # Reset the timer until the next resync
            self._t0 = now
        return self._client


def _run(query):
    return get_daily_UR(query)


def run_query(query, cache_key, expire=3600):
    memcached_client = memcached_discovery.get_client()
    if memcached_client is None:
        return _run(query)
    else:
        json = memcached_client.get(cache_key)
        if json is not None:
            df = json.read(json, orient='records')
        else:
            df = _run(query)
            memcached_client.set(cache_key, json.dumps(df), expire=expire)
        return df


def convert_coords(x1, y1):
    inProj = Proj(init='epsg:3857')
    outProj = Proj(init='epsg:4326')
    y2, x2 = transform(inProj, outProj, x1, y1)
    return x2, y2


memcached_discovery = MemcachedDiscovery()
