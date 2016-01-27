"""
.. module: dummyAxis
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

dummyCamera provides a dummy camera device for testing purposes.
You can use this file as a starting point when writing your own camera device module for pyFSRS.

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


class dummyCamera(module.Input):
    def __init__(self):
        module.Input.__init__(self)

        self.CCDwidth = 1024
        self.name = "Dummy Camera"

        # setup properties and convert dictionary to properties object
        prop = []
        prop.append({"label": "Phase Flip", "type": "choice", "value": 0, "choices": ["0 deg", "180 deg"]})
        self.parsePropertiesDict(prop)

    # return the band integral over the entire CCD using column 1
    def read(self):
        c, _, _ = self.readNframes(80)
        return c.sum() / float(len(c))

    # this is the camera function that returns a 3xN array containing the data from the camera driver
    # columns are: col2 / col3, col2, col3
    def readNframes(self, N, canQuit=None):

        time.sleep(float(N) / 1000)

        w = float(self.CCDwidth)

        # make random data
        data = np.random.rand(2 * N, self.CCDwidth)
        data[::2, :] = data[::2, :] + np.ones(data[::2, :].shape) * np.exp(-(np.arange(self.CCDwidth) - w / 2.0)**2 / (w / 10.0)**2)

        flip = bool(self.getPropertyByLabel("flip").getValue())

        # get chopped and unchopped
        A = np.mean(data[int(not flip)::2, :], axis=0)
        B = np.mean(data[int(flip)::2, :], axis=0)
        C = np.nan_to_num(A / B)

        return np.array([C, A, B])
