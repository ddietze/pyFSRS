"""
.. module: SR830
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

SR830 provides support for the Stanford SR830 Lock-In through pyVISA.
Iterates through all connected GPIB devices and adds a module for each SR830 that has been found.

..
   This file is part of the pyFSRS app.

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program. If not, see <http://www.gnu.org/licenses/>.

   Copyright 2014-2016 Daniel Dietze <daniel.dietze@berkeley.edu>.
"""
import time
import visa
import core.FSRSModule as module


# parse all GPIB devices and look how many SR830 are connected
def howMany():
    count = 0
    rm = visa.ResourceManager()
    res = rm.list_resources()
    for d in res:
        if d.find("GPIB") != -1:
            instr = rm.open_resource(d)
            if instr.query("*IDN?").find("SR830") != -1:
                count += 1
    print "Found %d SR830 LIAs" % count
    return count


# parse all GPIB devices and look where the SR830 can be found
# skp gives the number of occurrences that should be ignored
def locateSR830(skp=0):
    count = 0
    rm = visa.ResourceManager()
    res = rm.list_resources()
    for d in res:
        if d.find("GPIB") != -1:
            instr = rm.open_resource(d)
            if instr.query("*IDN?").find("SR830") != -1:
                count += 1
                if count > skp:
                    return d
    return ""


# main class
class SR830(module.Input):
    def __init__(self):
        module.Input.__init__(self)

        # assign module name
        self.name = "SR830 Lock-In"

        self.OFLTchoices = ["10 us", "30 us", "100 us", "300 us", "1 ms", "3 ms", "10 ms", "30 ms", "100 ms", "300 ms", "1 s", "3 s", "10 s", "30 s", "100 s", "300 s", "1 ks", "3 ks", "10 ks", "30 ks"]
        self.SENSchoices = ["2 nV/fA", "5 nV/fA", "10 nV/fA", "20 nV/fA", "50 nV/fA", "100 nV/fA", "200 nV/fA", "500 nV/fA", "1 uV/pA", "2 uV/pA", "5 uV/pA", "10 uV/pA", "20 uV/pA", "50 uV/pA", "100 uV/pA", "200 uV/pA", "500 uV/pA", "1 mV/nA", "2 mV/nA", "5 mV/nA", "10 mV/nA", "20 mV/nA", "50 mV/nA", "100 mV/nA", "200 mV/nA", "500 mV/nA", "1 V/uA"]
        self.CHANchoices = ["X", "Y", "R", "PHI"]

        # build properties dictionary
        prop = []
        prop.append({'label': "Address", "type": "label", "value": "", "event": None})
        prop.append({'label': "Channel", 'type': 'choice', 'value': 0, 'choices': self.CHANchoices, 'event': "write_settings"})
        prop.append({'label': "Sensitivity", 'type': 'choice', 'value': 0, 'choices': self.SENSchoices, 'event': "write_settings"})
        prop.append({'label': "Time Constant", 'type': 'choice', 'value': 0, 'choices': self.OFLTchoices, 'event': "write_settings"})
        prop.append({'label': "Wait Time (s)", "type": "input", "value": "0", "event": None})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)
        self.ready = False

    def initialize(self, others=[]):
        # count how many instances are before this one; this gives the number of SR830 instances I have to skip
        # for locating the correct address
        count = module.Input.initialize(self, others)
        adr = locateSR830(count)
        self.getPropertyByLabel("address").setValue(adr)
        self.connect()

    def shutdown(self):
        self.disconnect()

    # establish / end a pyVISA connection
    def connect(self, event=None):
        adr = self.getPropertyByLabel("address").getValue()
        if adr == "":
            self.ready = False
            return

        # connect to visa library
        rm = visa.ResourceManager()

        # open instrument
        self.instr = rm.open_resource(adr)

        # check whether its an SR830
        ID = self.instr.query("*IDN?")
        if ID.find("SR830") == -1:
            raise ValueError("Cannot connect to SR830 at address %s. ID says %s." % (adr, ID))

        # reset to default values
        self.instr.write("REST")
        self.instr.write("OUTX 1")

        self.ready = True

        # send configuration to properties
        self.read_settings()

    def disconnect(self):
        if self.ready:
            self.instr.write("OVRM 1")        # unblock the front panel of the SR830
        self.ready = False

    # copy settings from SR830 to properties
    def read_settings(self):
        if not self.ready:
            return

        SENS = int(self.instr.query("SENS?"))
        OFLT = int(self.instr.query("OFLT?"))

        self.getPropertyByLabel("sensitivity").setValue(SENS)
        self.getPropertyByLabel("time constant").setValue(OFLT)

    # write settings from properties to SR830
    def write_settings(self, event=None):
        if not self.ready:
            return

        SENS = self.getPropertyByLabel("sensitivity").getValue()
        OFLT = self.getPropertyByLabel("time constant").getValue()

        self.instr.write("SENS %d" % SENS)
        self.instr.write("OFLT %d" % OFLT)

    def read(self):
        if not self.ready:
            return 0

        # wait number of seconds
        time.sleep(abs(float(self.getPropertyByLabel("wait").getValue())))

        # now read input
        value = float(self.instr.query("OUTP? %d" % (self.getPropertyByLabel("channel").getValue() + 1)))

        return value
