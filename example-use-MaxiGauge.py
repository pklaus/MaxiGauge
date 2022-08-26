#!/usr/bin/env python

import yaml

# Load the module:
from PfeifferVacuum import MaxiGauge

if __name__ == '__main__':
    with open('settings.yml', 'r') as settings_file:
        settings = yaml.safe_load(settings_file)
        SERIAL_PORT = settings.get('serial_port', '/dev/ttyUSB0')

    # Initialize an instance of the MaxiGauge controller with
    # the handle of the serial terminal it is connected to
    mg = MaxiGauge(SERIAL_PORT)

    # Run the self check (not needed)
    print(mg.checkDevice())

    # Set device characteristics (here: change the display contrast)
    print("Set the display contrast to: %d" % mg.displayContrast(10))

    # Read out the pressure gauges
    print(mg.pressures())

    # Display the value of the pressure gauges for 20 repeated read outs
    for i in range(20):
        ps = mg.pressures()
        print("Sensor 1: %4e mbar" % ps[0].pressure + "Sensor 6: %4e mbar" % ps[5].pressure)
