#!/usr/bin/env python

from PfeifferVacuum import MaxiGauge


#mg = MaxiGauge('/dev/tty.usbserial', 9600, True) ### Debug Flag set to True
mg = MaxiGauge('/dev/tty.usbserial')

print(mg.checkDevice())

print("Set the display contrast to: %d" % mg.displayContrast(10))

print(mg.pressures())

for i in range(20):
    ps = mg.pressures()
    print "Sensor 1: %4e mbar" % ps[0].pressure + "Sensor 6: %4e mbar" % ps[5].pressure