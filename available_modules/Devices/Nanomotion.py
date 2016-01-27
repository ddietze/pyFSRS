"""
.. module: Nanomotion
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

Nanomotion provides a pyFSRS axis module for the Melles Griot NanoMover II.

It is assumed that the axis is used for a single pass optical delay stage and, therefore, positions are in fs.
This setting can easily be changed and adapted to individual needs by changing the value of `self.fs2mm`.

Only the first attached controller is used at the moment. Multiple controllers could be supported by implementing the `howMany` function.
However, multiple axes per controller are supported. Individual axes can be selected through a choice box. Only the active axis can be moved by external modules.

On startup, all motors are initialized and unparked. The current position is set to self.home (default: -3000.0 fs).
The axis then moves to 0.0. When decive is disconnected, all motors go to self.home and park.

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
import wx
import visa
import time
import threading
import core.FSRSModule as module


# parse all GPIB devices and look where the Nanomotion can be found
# skips the first skp hits
def locateNanomotion(skp=0):
    count = 0
    rm = visa.ResourceManager()
    res = rm.list_resources()
    for d in res:
        if d.find("GPIB") != -1:
            instr = rm.open_resource(d)
            if instr.query("*IDN?").lower().find("mg_nano") != -1:
                count += 1
                if count > skp:
                    return d
    return ""


# Notes on Operation:
# when device is connected, all motors are initialized and unparked
# the current position is set to self.home (default: -3000.0 fs)
# the axis then moves to 0.0
# when decive is disconnected, all motors go to self.home and park
#
# uses a wx.Timer to periodically update the stage position
class Nanomotion(module.Axis):
    def __init__(self):
        module.Axis.__init__(self)

        self.name = "NanoMotion II Axis Controller"
        self.fs2mm = 2.9979e8 * 1e3 * 1e-15 / 2   #: mm stage travel / fs delay
        self.home = -3000.0                       #: homing position = most negative position allowed
        self.motors = []

        # build properties dictionary
        prop = []
        prop.append({'label': 'Address', 'type': 'label', 'value': '', 'event': None})
        prop.append({'label': 'Axis', 'type': 'choice', 'choices': self.motors, 'value': 0, 'event': None})
        prop.append({'label': 'Home (fs)', 'type': 'label', 'value': str(self.home), 'event': None})
        prop.append({'label': 'Current Position (fs)', 'type': 'label', 'value': '0.0'})
        prop.append({'label': 'Target (fs)', 'type': 'input', 'value': '0', 'info': 'int', 'event': None})
        prop.append({'label': 'Movement', 'type': 'button', 'value': 'Start', 'event': 'onStartStop'})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)
        self.ready = False

        # make a wx.Timer object to update the position of the stage
        self.updTimer = wx.Timer()
        self.updTimer.Bind(wx.EVT_TIMER, self.updatePosition)

    def initialize(self, others=[]):
        # count how many instances are before this one; this gives the number of instances I have to skip
        # for locating the correct address
        count = module.Axis.initialize(self, others)
        self.getPropertyByLabel("address").setValue(locateNanomotion(count))
        self.connect()

    def shutdown(self):
        try:
            self.updTimer.cancel()
        except:
            pass
        self.disconnect()

    # establish / end a pyVISA connection
    def connect(self, event=None):
        adr = self.getPropertyByLabel("address").getValue()
        if not adr:
            self.ready = False
            return

        # connect to visa library
        rm = visa.ResourceManager()

        # open instrument
        self.instr = rm.open_resource(adr)

        # check whether its a NanoMotion
        ID = self.instr.query("*IDN?")
        if ID.lower().find("mg_nano") == -1:
            raise ValueError("Cannot connect to NanoMotion II at address %s. ID says %s." % (adr, ID))

        # reset to default values
        self.instr.write("*RST")

        # activate GPIB remote operation
        self.instr.write("*REM")

        # get available motors and update list
        self.motors = []
        for i in range(1, 17):
            if self.instr.query("RS,%d" % i) != "Command Error":
                self.motors.append(str(i))

        self.getPropertyByLabel("axis").setChoices(self.motors)

        # unpark all motors
        self.instr.write("UA")

        # set units to MM
        # set current position to self.home and move to 0
        for m in self.motors:
            self.instr.write("WU,%s,MM" % m)
            self.instr.write("WP,%s,%f" % (m, self.home * self.fs2mm))
            self.instr.write("WAL,%s,%f" % (m, self.home * self.fs2mm))
            WAR = float(self.instr.query("RAR,%s" % m).split(",")[1])
            self.instr.write("WAR,%s,%f" % (m, WAR + self.home * self.fs2mm))
            self.instr.write("MA,%s,0.0" % m)

        self.ready = True

        # read position and set value
        self.updatePosition()

    def disconnect(self):
        if self.ready:
            # move to home position
            for m in self.motors:
                self.instr.write("MA,%s,%f" % (m, self.home * self.fs2mm))

            # wait for all motors to stop
            while(1):
                time.sleep(0.1)
                moving = False
                for m in self.motors:
                    if self.instr.query("RS,%s" % m).split(",")[1] != "OK":
                        moving = True
                        break
                if not moving:
                    break

            # park all motors
            self.instr.write("PA")
        self.ready = False

    def getCurrentMotor(self):
        id = self.getPropertyByLabel("axis").getValue()
        return int(self.motors[id])

    def onStartStop(self, event):
        if self.getPropertyByLabel("movement").getValue() == "Start":
            pos = float(self.getPropertyByLabel("target").getValue())
            self.goto(pos)
        else:
            self.instr.write("S")    # stop all motors

    def updatePosition(self, event=None):
        # read position and set value
        self.getPropertyByLabel("position").setValue("%.f" % self.pos())

        # restart timer
        if self.is_moving():
            self.updTimer = threading.Timer(0.3, self.updatePosition)
            self.updTimer.start()

    # return current position
    def pos(self):
        try:
            return float(self.instr.query("RP,%d" % self.getCurrentMotor()).split(",")[1]) / self.fs2mm
        except:
            return 0.0

    # goto new position
    def goto(self, pos):
        if not self.ready:
            return
        print "goto", pos
        # move to new position
        self.instr.write("MA,%d,%f" % (self.getCurrentMotor(), pos * self.fs2mm))
        # start update timer
        self.updTimer = threading.Timer(0.3, self.updatePosition)
        self.updTimer.start()

    # should return True if stage is still moving
    def is_moving(self):
        if not self.ready:
            return False
        return (self.instr.query("RS,%d" % self.getCurrentMotor()).split(",")[1] == "MV")
