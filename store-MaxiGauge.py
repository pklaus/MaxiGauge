#!/usr/bin/env python

### Load the module:
from PfeifferVacuum import MaxiGauge, MaxiGaugeError
import time
import sys

### Initialize an instance of the MaxiGauge controller with
### the handle of the serial terminal it is connected to
mg = MaxiGauge('/dev/ttyUSB1')
logfile = file('measurement-data.txt', 'a')

### Read out the pressure gauges
while True:
    startTime = time.time()

    try:
        ps = mg.pressures()
    except MaxiGaugeError, mge:
        print mge
        continue
    line = "%d, " % int(time.time())
    for sensor in ps:
        #print sensor
        if sensor.status in [0,1,2]:
            line += "%.3E" % sensor.pressure
        line += ", "
    line = line[0:-2] # omit the last comma and space
    print line
    sys.stdout.flush()
    logfile.write(line+'\n')
    logfile.flush()

    # do this every second
    endTime = time.time()-startTime
    time.sleep(max([0.0, 1. - endTime]))
