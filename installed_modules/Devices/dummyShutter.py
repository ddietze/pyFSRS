"""
.. module: dummyShutter
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

dummyShutter provides a dummy output device for testing purposes, in this case a digital output.
You can use this file as a starting point when writing your own output device module for pyFSRS.

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
import core.FSRSModule as module


def howMany():
    return 1


class dummyShutter(module.Output):
    def __init__(self):
        module.Output.__init__(self)
        self.name = "Dummy Shutter"

        prop = []
        prop.append({"label": "Slope", "type": "choice", "choices": ["Open on High", "Open on Low"], "value": 0, "event": "onToggle"})
        prop.append({"label": "Control", "type": "toggle", "value": 0, "info": "OPEN/CLOSE", "event": "onToggle"})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

    def onToggle(self, event):
        self.write(self.getPropertyByLabel("control").getValue())

    # change status of shutter
    # value = False = LOW
    # value = True = HIGH
    def write(self, value):

        status = bool(value) ^ bool(self.getPropertyByLabel("slope").getValue())
        if status:
            print "Shutter open"
        else:
            print "Shutter closed"
