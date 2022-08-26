#!/usr/bin/env python

import time
import sys
import yaml

# Load the module:
from PfeifferVacuum import MaxiGauge, MaxiGaugeError

if __name__ == '__main__':
    with open('settings.yml', 'r') as settings_file:
        settings = yaml.safe_load(settings_file)
        SERIAL_PORT = settings.get('serial_port', '/dev/ttyUSB0')
        LOGFILE = settings.get('logfile_name', 'measurement-data.txt')

    # Initialize an instance of the MaxiGauge controller with
    # the handle of the serial terminal it is connected to
    mg = MaxiGauge(SERIAL_PORT)

    with open(LOGFILE, 'a') as logfile:
        # Read out the pressure gauges
        while True:
            startTime = time.time()

            try:
                ps = mg.pressures()
            except MaxiGaugeError as mge:
                print(mge)
                continue
            line = "%d, " % int(time.time())
            for sensor in ps:
                # print sensor
                if sensor.status in [0, 1, 2]:
                    line += "%.3E" % sensor.pressure
                line += ", "
            line = line[0:-2]  # omit the last comma and space
            print(line)
            sys.stdout.flush()
            logfile.write(line + '\n')
            logfile.flush()

            # do this every second
            endTime = time.time() - startTime
            time.sleep(max([0.0, 1. - endTime]))
