#!/usr/bin/env python
# -*- encoding: UTF8 -*-

# Author: Philipp Klaus, philipp.l.klaus AT web.de

# This file is part of PfeifferVacuum.py.
#
# PfeifferVacuum.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PfeifferVacuum.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PfeifferVacuum.py. If not, see <http://www.gnu.org/licenses/>.


### This module depends on PySerial, a cross platform Python module
### to leverage the communication with the serial port.
### http://pyserial.sourceforge.net/pyserial.html#installation
### If you have `pip` installed on your computer, getting PySerial is as easy as
### pip install pyserial

import serial

class MaxiGauge (object):
    def __init__(self, serialPort, baud=9600, debug=False):
        self.debug=debug
        try:
            self.connection = serial.Serial(serialPort, baudrate=baud, timeout=0.2)
        except serial.serialutil.SerialException as se:
            raise MaxiGaugeError(se)
        #self.send(C['ETX']) ### We might reset the connection first, but it doesn't really matter:

    def checkDevice(self):
        message = "The Display Contrast is currently set to %d (out of 20).\n" % self.displayContrast()
        message += "Keys since MaxiGauge was switched on: %s (out of 1,2,3,4,5).\n" % ", ".join( map (str, self.pressedKeys()) )
        return message

    def pressedKeys(self):
        keys = int(self.send('TKB',1)[0])
        pressedKeys = []
        for i in [4,3,2,1,0]: # It's got 5 keys
            if keys/2**i == 1:
                pressedKeys.append(i+1)
                keys = keys%2**i
        pressedKeys.reverse()
        return pressedKeys

    def displayContrast(self,newContrast=-1):
        if newContrast == -1: return int(self.send('DCC',1)[0])
        else: return int(self.send('DCC,%d' % (newContrast,) ,1)[0])

    def pressures(self):
        return [self.pressure(i+1) for i in range(6)]

    def pressure(self, sensor):
        if sensor < 1 or sensor >6: raise MaxiGaugeError('Sensor can only be between 1 and 6. You choose ' + str(sensor))
        reading = self.send('PR%d' % sensor, 1)  ## reading will have the form x,x.xxxEsx <CR><LF> (see p.88)
        try:
            r = reading[0].split(',')
            status = int(r[0])
            pressure = float(r[-1])
        except:
            raise MaxiGaugeError("Problem interpreting the returned line:\n%s" % reading)
        return PressureReading(sensor, status, pressure)

    def debugMessage(self, message):
        if self.debug: print(repr(message))

    def send(self, mnemonic, numEnquiries = 0):
        self.connection.flushInput()
        self.write(mnemonic+LINE_TERMINATION)
        #if mnemonic != C['ETX']: self.read()
        #self.read()
        self.getACQorNAK()
        response = []
        for i in range(numEnquiries):
            self.enquire()
            response.append(self.read())
        return response

    def write(self,what):
        self.debugMessage(what)
        self.connection.write(what)

    def enquire(self):
        self.write(C['ENQ'])

    def read(self):
        data = ""
        while True:
            x = self.connection.read()
            self.debugMessage(x)
            data += x
            if len(data)>1 and data[-2:]==LINE_TERMINATION:
                break
        return data[:-len(LINE_TERMINATION)]

    def getACQorNAK(self):
        returncode = self.connection.readline()
        self.debugMessage(returncode)
        ## The following is usually expected but our MaxiGauge controller sometimes forgets this parameter... That seems to be a bug with the DCC command.
        #if len(returncode)<3: raise MaxiGaugeError('Only received a line termination from MaxiGauge. Was expecting ACQ or NAK.')
        if len(returncode)<3: self.debugMessage('Only received a line termination from MaxiGauge. Was expecting ACQ or NAK.')
        if len(returncode)>2 and returncode[-3] == C['NAK']:
            self.enquire()
            returnedError = self.read()
            error = str(returnedError).split(',' , 1)
            print repr(error)
            errmsg = { 'System Error': ERR_CODES[0][int(error[0])] , 'Gauge Error': ERR_CODES[1][int(error[1])] }
            raise MaxiGaugeNAK(errmsg)
        #if len(returncode)>2 and returncode[-3] != C['ACQ']: raise MaxiGaugeError('Expecting ACQ or NAK from MaxiGauge but neither were sent.')
        if len(returncode)>2 and returncode[-3] != C['ACQ']: self.debugMessage('Expecting ACQ or NAK from MaxiGauge but neither were sent.')
        # if no exception raised so far, the interface is just fine:
        return returncode[:-(len(LINE_TERMINATION)+1)]
        
    def disconnect(self):
        #self.send(C['ETX'])
        if hasattr(self, 'connection') and self.connection: self.connection.close()

    def __del__(self):
        self.disconnect()

class PressureReading(object):
    def __init__(self, id, status, pressure):
        if int(id) not in range(1,7): raise MaxiGaugeError('Pressure Gauge ID must be between 1-6')
        self.id = int(id)
        if int(status) not in PRESSURE_READING_STATUS.keys(): raise MaxiGaugeError('The Pressure Status must be in the range %s' % PRESSURE_READING_STATUS.keys())
        self.status = int(status)
        self.pressure = float(pressure)

    def statusMsg(self):
        return PRESSURE_READING_STATUS[self.status]

    def __repr__(self):
        return "Gauge #%d: Status %d (%s), Pressure: %f mbar\n" % (self.id, self.status, self.statusMsg(), self.pressure)


### ------ now we define the exceptions that could occur ------

class MaxiGaugeError(Exception):
    pass

class MaxiGaugeNAK(MaxiGaugeError):
    pass

### ------- Control Symbols as defined on p. 81 of the english
###        manual for the Pfeiffer Vacuum TPG256A  -----------
C = { 
  'ETX': "\x03", # End of Text (Ctrl-C)   Reset the interface
  'CR':  "\x0D", # Carriage Return        Go to the beginning of line
  'LF':  "\x0A", # Line Feed              Advance by one line
  'ENQ': "\x05", # Enquiry                Request for data transmission
  'ACQ': "\x06", # Acknowledge            Positive report signal
  'NAK': "\x15", # Negative Acknowledge   Negative report signal
  'ESC': "\x1b", # Escape
}

LINE_TERMINATION=C['CR']+C['LF'] # CR, LF and CRLF are all possible (p.82)

### Mnemonics as defined on p. 85
M = [
  'BAU', # Baud rate                           Baud rate                                    95
  'CAx', # Calibration factor Sensor x         Calibration factor sensor x (1 ... 6)        92
  'CID', # Measurement point names             Measurement point names                      88
  'DCB', # Display control Bargraph            Bargraph                                     89
  'DCC', # Display control Contrast            Display control contrast                     90
  'DCD', # Display control Digits              Display digits                               88
  'DCS', # Display control Screensave          Display control screensave                   90
  'DGS', # Degas                               Degas                                        93
  'ERR', # Error Status                        Error status                                 97
  'FIL', # Filter time constant                Filter time constant                         92
  'FSR', # Full scale range of linear sensors  Full scale range of linear sensors           93
  'LOC', # Parameter setup lock                Parameter setup lock                         91
  'NAD', # Node (device) address for RS485     Node (device) address for RS485              96
  'OFC', # Offset correction                   Offset correction                            93
  'OFC', # Offset correction                   Offset correction                            93
  'PNR', # Program number                      Program number                               98
  'PRx', # Status, Pressure sensor x (1 ... 6) Status, Pressure sensor x (1 ... 6)          88
  'PUC', # Underrange Ctrl                     Underrange control                           91
  'RSX', # Interface                           Interface                                    94
  'SAV', # Save default                        Save default                                 94
  'SCx', # Sensor control                      Sensor control                               87
  'SEN', # Sensor on/off                       Sensor on/off                                86
  'SPx', # Set Point Control Source for Relay xThreshold value setting, Allocation          90
  'SPS', # Set Point Status A,B,C,D,E,F        Set point status                             91
  'TAI', # Test program A/D Identify           Test A/D converter identification inputs    100
  'TAS', # Test program A/D Sensor             Test A/D converter measurement value inputs 100
  'TDI', # Display test                        Display test                                 98
  'TEE', # EEPROM test                         EEPROM test                                 100
  'TEP', # EPROM test                          EPROM test                                   99
  'TID', # Sensor identification               Sensor identification                       101
  'TKB', # Keyboard test                       Keyboard test                                99
  'TRA', # RAM test                            RAM test                                     99
  'UNI', # Unit of measurement (Display)       Unit of measurement (pressure)               89
  'WDT', # Watchdog and System Error Control   Watchdog and system error control           101
]


### Error codes as defined on p. 97
ERR_CODES = [
  {
        0: 'No error',
        1: 'Watchdog has responded',
        2: 'Task fail error',
        4: 'IDCX idle error',
        8: 'Stack overflow error',
       16: 'EPROM error',
       32: 'RAM error',
       64: 'EEPROM error',
      128: 'Key error',
     4096: 'Syntax error',
     8192: 'Inadmissible parameter',
    16384: 'No hardware',
    32768: 'Fatal error'
  } ,
  {
        0: 'No error',
        1: 'Sensor 1: Measurement error',
        2: 'Sensor 2: Measurement error',
        4: 'Sensor 3: Measurement error',
        8: 'Sensor 4: Measurement error',
       16: 'Sensor 5: Measurement error',
       32: 'Sensor 6: Measurement error',
      512: 'Sensor 1: Identification error',
     1024: 'Sensor 2: Identification error',
     2048: 'Sensor 3: Identification error',
     4096: 'Sensor 4: Identification error',
     8192: 'Sensor 5: Identification error',
    16384: 'Sensor 6: Identification error',
  }
]

### pressure status as defined on p.88
PRESSURE_READING_STATUS = {
  0: 'Measurement data okay',
  1: 'Underrange',
  2: 'Overrange',
  3: 'Sensor error',
  4: 'Sensor off',
  5: 'No sensor',
  6: 'Identification error'
}
