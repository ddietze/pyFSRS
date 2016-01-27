"""
.. module: dummyDAQ
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

dummyDAQ provides a dummy input device for testing purposes.
You can use this file as a starting point when writing your own input device module for pyFSRS.

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
import numpy as np
import core.FSRSModule as module


def howMany():
    return 1


class dummyDAQ(module.Input):
    def __init__(self):
        module.Input.__init__(self)

        self.name = "Dummy DAQ"

        prop = []
        prop.append({"label": "Amplitude", "type": "input", "value": "1.0"})
        prop.append({"label": "Offset", "type": "input", "value": "0.0"})
        prop.append({'label': "Wait Time (s)", "type": "input", "value": "0"})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

    # this is the only additional function an input device has to have
    # returns some value
    def read(self):

        # wait number of seconds
        time.sleep(abs(float(self.getPropertyByLabel("wait").getValue())))

        return (np.random.rand(1) - 0.5) * float(self.getPropertyByLabel("amplitude").getValue()) + float(self.getPropertyByLabel("offset").getValue())
