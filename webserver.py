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


### HowTo
# To run this Bottle web application, you have to install
# the python modules
# * bottle
# * cherrypy
# You can do this via `pip install bottle` etc.
# Then you should adjust the virtual serial port setting in this file.
# When finished, run this file via `./webserver.py`
# and you should be able to reach the site via
# http://localhost:8080

device = '/dev/ttyUSB0'
logfilename = 'measurement-data.txt'

### Load the module:
from PfeifferVacuum import MaxiGauge, MaxiGaugeError

from bottle import Bottle, run, request, static_file, HTTPError, PluginError, response

import json

import inspect

import datetime

class MaxiGaugePlugin(object):
    ''' This plugin passes a MaxiGauge class handle to route callbacks
that accept a `maxigauge` keyword argument.
It is based on the example on
http://bottlepy.org/docs/stable/plugindev.html#plugin-example-sqliteplugin
'''
    name = 'maxigauge'
    api = 2

    def __init__(self, device, keyword='maxigauge'):
         self.device = device
         self.keyword = keyword

    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
keyword argument.'''
        for other in app.plugins:
            if not isinstance(other, MaxiGaugePlugin): continue
            if other.keyword == self.keyword:
                raise PluginError("Found another MaxiGauge plugin with "\
                "conflicting settings (non-unique keyword).")
        try:
            ### Initialize an instance of the MaxiGauge controller with
            ### the handle of the serial terminal it is connected to
            self.maxigauge = MaxiGauge(self.device)
            self.maxigauge.start_continuous_pressure_updates(.4, 75)
        except Exception, e:
            raise PluginError("Could not connect to the MaxiGauge (on port %s). Error: %s" % (self.device, e) )

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
            except NameError, e:
                raise HTTPError(503, "MaxiGauge not available: " + str(e) )
            finally:
                #self.maxigauge.disconnect()
                pass
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper

    def close(self):
        self.maxigauge.disconnect()

import time

api = Bottle()
mg_plugin = MaxiGaugePlugin(device)
api.install(mg_plugin)



#@api.route('/pressure/data')
#def pressure_data(maxigauge):
#    # modeled after http://code.shutterstock.com/rickshaw/guide/data.json
#    status = dict()
#
#    ### Read out the pressure gauges
#    pressure_value = []
#    ps = maxigauge.pressures()
#    for i, sensor in enumerate(ps):
#        name = 'Pressure Gauge %d' % (i+1)
#        if sensor.status in [0,1,2]:
#            ret_val['color'] = 'blue'
#            pressure_value.append(sensor.pressure)
#            status.append(pressure_value)
#
#    return status

@api.route('/pressures')
def pressure_data(maxigauge):
    status = dict()
    ### Read out the pressure gauges
    #ps = maxigauge.pressures()
    ps = maxigauge.cached_pressures
    for i, sensor in enumerate(ps):
        if sensor.status in [0,1,2]:
            status['gauge %d' % (i+1)] = sensor.pressure
    return status

#@api.route('/cached_pressure_history_csv')
#def cached_pressure_history_csv(maxigauge):
#    try:
#        number_of_lines = int(request.query.lines)
#    except:
#        return to_csv(maxigauge.history)
#    print_every = len(maxigauge.history) / number_of_lines
#    #response.content_type = 'text/csv'
#    response.content_type = 'text/plain'
#    return to_csv(maxigauge.history[::print_every])

#def to_csv(data):
#    output = []
#    for row in data:
#        output.append("%d%s" % (row[0], "".join([", %.3E" % val for val in row[1:]] )))

from os.path import getsize
@api.route('/pressure_history_csv')
def pressure_history_csv(maxigauge):
    maxigauge.flush_logfile()
    try:
        number_of_lines = int(request.query.lines)
    except:
        return static_file(logfilename, root='./', mimetype='text/csv', download=('pressure_history_%s.csv' % datetime.date.today().isoformat()) )
    bytes = getsize(logfilename)
    approximate_number_of_lines = (bytes - 33) / 60
    print_every = approximate_number_of_lines / (number_of_lines - 1)
    #response.content_type = 'text/csv'
    response.content_type = 'text/plain'
    request.query.fast
    import subprocess
    return subprocess.check_output(['./extract_every_nth_line', 'measurement-data.txt', str(print_every)])
    #try:
    #    request.query.fast
    #    import subprocess
    #    return subprocess.check_output(['./extract_every_nth_line', 'measurement-data.txt', str(100)])
    #except AttributeError:
    #    pass
    #output = []
    #i = -1
    #for line in open( logfilename ):
    #    if (i < 0) or (i % print_every == 0):
    #        output.append(line)
    #    i += 1
    #return output

retdata = []
@api.route('/pressure_history')
def pressure_history(maxigauge):
    global retdata
    response.content_type = 'application/json'
    if len(retdata)>0: return json.dumps(retdata)
    maxigauge.flush_logfile()
    f = open( logfilename, 'r' )
    import csv
    log = csv.reader(f)

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
            color = 'lightblue' if n%2 == 0 else 'steelblue'
            retdata.append({ 'name': fieldnames[n], 'data': [], 'color': color })
    
    i = 0
    for row in log:
        if len(row) != len(fieldnames): continue
        i = i + 1
        if i%100 != 1: continue
        for k,j in enumerate(cols):
            retdata[k]['data'].append({'x': int(row[0]), 'y': 0.0 if row[j].strip() == '' else float(row[j])})
    return json.dumps(retdata)

#@api.route('/pressures')
#def pressures(maxigauge):
#    status = dict()
#
#    ### Read out the pressure gauges
#    pressure_values = []
#    ps = maxigauge.pressures()
#    status['system_time'] = int(time.time())
#    for sensor in ps:
#        #print sensor
#        if sensor.status in [0,1,2]:
#            pressure_values.append(sensor.pressure)
#        else
#            pressure_values.append(NaN)
#    status['pressure_values'] = pressure_values
#
#    return status


root = Bottle()
root.mount(api, '/api')

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

print "Press Ctrl-C twice to stop this web server!"

## Run with cherrypy server via IPv4:
run( root, server='cherrypy', host="0.0.0.0", port=8080)
## Run with cherrypy server via IPv6:
#run( root, server='cherrypy', host="::", port=8080)

## Run with bottle's standard server (IPv4):
#run( root, host="localhost", port=8080)
#run( root, host="0.0.0.0", port=8080)
#run( root, host="0.0.0.0", port=8080, debug=True)
