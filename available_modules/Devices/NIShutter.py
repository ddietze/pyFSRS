"""
.. module: NIShutter
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

NIShutter provides a **digital** output module for controlling optical shutters based on PyDAQmx.
It opens the device specified by the address in its shutter-property, which is hardcoded in the module.
If you would like to use several independent shutters or digital outputs, copy and rename this module and file.

Does not change the initial value of the outputs upon startup.

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
import PyDAQmx as daq
import numpy as np
import ctypes
import core.FSRSModule as module


class NIShutter(module.Output):
    def __init__(self):
        module.Output.__init__(self)
        self.name = "NI DAQ Shutter"

        self.lastState = 0
        self.slope = 255

        self.NIdaq = daq.Task()    # create pyDAQmx task object

        prop = []
        prop.append({"label": "Shutter DAQ", "type": "label", "value": "Dev1/port0"})
        prop.append({"label": "Channel", "type": "spin", "value": 0, "info": (0, 7), "event": "onChangeChannel"})
        prop.append({"label": "Slope", "type": "choice", "choices": ["Open on Low", "Open on High"], "value": 1, "event": "onChangeSlope"})
        prop.append({"label": "Control", "type": "toggle", "value": 0, "info": "OPEN", "event": "onToggle"})
        self.parsePropertiesDict(prop)

    def initialize(self, others=[]):
        # connect task to digital out channels 0..7
        # creating one channel per line
        self.NIdaq.CreateDOChan(self.getPropertyByLabel("shutter").getValue(), "", daq.DAQmx_Val_ChanForAllLines)

    def onChangeChannel(self, event):
        channelBitmask = (1 << self.getPropertyByLabel("channel").getValue())

        slope = bool(self.slope & channelBitmask)
        self.getPropertyByLabel("slope").setValue(slope)

        self.updateToggleButton()

    def onChangeSlope(self, event):
        channelBitmask = (1 << self.getPropertyByLabel("channel").getValue())

        slope = self.getPropertyByLabel("slope").getValue()
        if slope:
            self.slope |= channelBitmask
        else:
            self.slope &= ~channelBitmask

        self.onToggle(None)

    def onToggle(self, event):
        self.write(self.getPropertyByLabel("control").getValue())

    def updateToggleButton(self):
        channelBitmask = (1 << self.getPropertyByLabel("channel").getValue())
        isOpened = ((self.lastState & channelBitmask) == (self.slope & channelBitmask))

        if isOpened:
            self.getPropertyByLabel("control").setInfo("PRESS TO CLOSE")
            self.getPropertyByLabel("control").setValue(1)
        else:
            self.getPropertyByLabel("control").setInfo("PRESS TO OPEN")
            self.getPropertyByLabel("control").setValue(0)

    # change status of shutter
    # value = False = LOW
    # value = True = HIGH
    def write(self, value):

        # prepare new state bitmask without changing the other channels
        writeArray = self.lastState
        channelBitmask = (1 << self.getPropertyByLabel("channel").getValue())
        slope = bool(self.slope & channelBitmask)

        if value == slope:                    # equivalent to XNOR, if true: send 1
            writeArray |= channelBitmask
        else:                                # send 0
            writeArray &= ~channelBitmask

        # store state
        self.lastState = writeArray

        # send configuration to DAQ
        sampsPerChanWritten = daq.int32()
        writeArray = np.array(writeArray, dtype=daq.uInt8)
        self.NIdaq.WriteDigitalU8(1, True, 0, daq.DAQmx_Val_GroupByChannel, writeArray, ctypes.byref(sampsPerChanWritten), None)

        # update GUI
        self.isOpened = bool(value)
        self.updateToggleButton()
