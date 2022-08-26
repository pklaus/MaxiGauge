#!/usr/bin/env python
# -*- encoding: UTF8 -*-

# Author: Philipp Klaus, philipp.l.klaus AT web.de


# This file is part of netio230a.
#
# netio230a is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# netio230a is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with netio230a. If not, see <http://www.gnu.org/licenses/>.


# HowTo
# To run this Bottle web application, you have to install
# the python modules
# * bottle
# * cherrypy
# You can do this via `pip install bottle` etc.
# Then you should adjust the virtual serial port setting in this file.
# When finished, run this file via `./webserver.py`
# and you should be able to reach the site via
# http://localhost:8080

import csv
import datetime
import inspect
import json
import yaml

from os.path import getsize

from bottle import Bottle, run, request, static_file, HTTPError, PluginError, response
# Load the module:
from PfeifferVacuum import MaxiGauge

with open('settings.yml', 'r') as settings_file:
    settings = yaml.safe_load(settings_file)
    DEVICE = settings.get('serial_port', '/dev/ttyUSB0')
    LOGFILE_NAME = settings.get('logfile_name', 'measurement-data.txt')


class MaxiGaugePlugin(object):
    """
    This plugin passes a MaxiGauge class handle to route callbacks
    that accept a `maxigauge` keyword argument.
    It is based on the example on
    http://bottlepy.org/docs/stable/plugindev.html#plugin-example-sqliteplugin
    """
    name = 'maxigauge'
    api = 2

    def __init__(self, device, keyword='maxigauge'):
        self.device = device
        self.keyword = keyword

    def setup(self, app):
        """
        Make sure that other installed plugins don't affect the same keyword argument.
        """
        for other in app.plugins:
            if not isinstance(other, MaxiGaugePlugin):
                continue
            if other.keyword == self.keyword:
                raise PluginError("Found another MaxiGauge plugin with conflicting settings (non-unique keyword).")
        try:
            # Initialize an instance of the MaxiGauge controller with
            # the handle of the serial terminal it is connected to
            self.maxigauge = MaxiGauge(self.device)
            self.maxigauge.start_continuous_pressure_updates(.4, 75)
        except Exception as e:
            raise PluginError("Could not connect to the MaxiGauge (on port %s). Error: %s" % (self.device, e))

    def apply(self, callback, context):
        keyword = self.keyword
        # Test if the original callback accepts a 'maxigauge' keyword.
        # Ignore it if it does not need a handle.
        args = inspect.getargspec(context.callback)[0]
        if keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            maxigauge = self.maxigauge
            # Add the connection handle as a keyword argument.
            kwargs[keyword] = maxigauge

            try:
                rv = callback(*args, **kwargs)
            except NameError as e:
                raise HTTPError(503, "MaxiGauge not available: " + str(e))
            finally:
                pass

            return rv

        # Replace the route callback with the wrapped one.
        return wrapper

    def close(self):
        self.maxigauge.disconnect()


api = Bottle()
mg_plugin = MaxiGaugePlugin(DEVICE)
api.install(mg_plugin)


@api.route('/pressures')
def pressure_data(maxigauge):
    status = dict()
    # Read out the pressure gauges
    ps = maxigauge.cached_pressures
    for i, sensor in enumerate(ps):
        if sensor.status in [0, 1, 2]:
            status['gauge %d' % (i + 1)] = sensor.pressure

    return status


@api.route('/pressure_history_csv')
def pressure_history_csv(maxigauge):
    maxigauge.flush_logfile()
    try:
        number_of_lines = int(request.query.lines)
    except:
        return static_file(LOGFILE_NAME, root='./', mimetype='text/csv',
                           download=('pressure_history_%s.csv' % datetime.date.today().isoformat()))

    bytes = getsize(LOGFILE_NAME)
    approximate_number_of_lines = (bytes - 33) / 60
    print_every = approximate_number_of_lines / (number_of_lines - 1)
    response.content_type = 'text/plain'
    request.query.fast
    import subprocess
    return subprocess.check_output(['./extract_every_nth_line', LOGFILE_NAME, str(print_every)])


retdata = []


@api.route('/pressure_history')
def pressure_history(maxigauge):
    global retdata
    response.content_type = 'application/json'
    if len(retdata) > 0:
        return json.dumps(retdata)
    maxigauge.flush_logfile()

    with open(LOGFILE_NAME, 'r') as logfile:
        log = csv.reader(logfile)

    # Get the 1st line, assuming it contains the column titles
    fieldnames = log.next()

    cols = []
    i = 0
    for fieldname in fieldnames:
        if fieldname.strip() != "" and fieldname != 'Seconds':
            cols.append(i)
        i += 1

    retdata = []
    for n in cols:
        color = 'lightblue' if n % 2 == 0 else 'steelblue'
        retdata.append({'name': fieldnames[n], 'data': [], 'color': color})

    i = 0
    for row in log:
        if len(row) != len(fieldnames):
            continue
        i = i + 1
        if i % 100 != 1:
            continue
        for k, j in enumerate(cols):
            retdata[k]['data'].append({'x': int(row[0]), 'y': 0.0 if row[j].strip() == '' else float(row[j])})
    return json.dumps(retdata)


root = Bottle()
root.mount('/api', api)


@root.route('/static/<path:path>')
def static(path):
    return static_file(path, root='./web_resources')


@root.route('/live_cubism')
def live_cubism():
    return static('live_cubism.html')


@root.route('/history_rickshaw')
def history_rickshaw():
    return static('history_rickshaw.html')


@root.route('/digital-display')
def digital_display():
    return static('digital-display.html')


@root.route('/live')
def live():
    return static('live.html')


@root.route('/history')
def history():
    return static('history.html')


@root.route('/')
def index():
    return static('index.html')


if __name__ == '__main__':
    # Run with cherrypy server via IPv4:
    run(root, server='cherrypy', host="0.0.0.0", port=8080)
    # Run with cherrypy server via IPv6:
    # run(root, server='cherrypy', host="::", port=8080)

    # Run with bottle's standard server (IPv4):
    # run(root, host="0.0.0.0", port=8080)
