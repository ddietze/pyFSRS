"""
.. module: dummyAxis
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

dummyAxis provides a dummy axis device for testing purposes.
You can use this file as a starting point when writing your own axis device module for pyFSRS.

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
# base class
import core.FSRSModule as module


def howMany():
    return 1


class dummyAxis(module.Axis):
    """A prototype for an axis module for pyFSRS.
    """
    def __init__(self):
        module.Axis.__init__(self)

        self.name = "Dummy Axis"

        prop = []
        prop.append({"label": "Axis", "type": "label", "value": ""})
        prop.append({"label": "Position", "type": "input", "value": "0.0", "event": "onMove"})
        prop.append({"label": "Speed", "type": "choice", "value": 0, "choices": ["fast", "slow"], "event": None})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

    def initialize(self, others=[]):
        count = module.Axis.initialize(self, others)
        self.getPropertyByLabel("axis").setValue("#" + str(count + 1))

    # return current position
    def pos(self):
        return self.position

    # goto new position
    def goto(self, pos):
        self.position = pos
        print "moved to", pos

    # should return True if stage is still moving
    def is_moving(self):
        return False

    def onMove(self, event):
        pos = float(self.getPropertyByLabel("position").getValue())
        self.goto(pos)
