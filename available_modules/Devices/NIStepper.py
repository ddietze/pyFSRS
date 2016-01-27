"""
.. module: NIStepper
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

NIStepper provides an axis module for 4-coil stepper motors controlled by a Darlington array and a National Instruments DAQ board through pyDAQmx.
The hardware settings and a variable number of motors are setup through self.motors.
Motor positions are in units of (micro-) steps. If you want to change this behaviour, change the value of `self.units2steps` and the type of the target from `int` to `float`.

Upon startup, all channels are set to LOW, i.e., no current. The same is true in between steps to minimize current flow and heat load.
As a consequence, the motors should only be used for applications where they do not have to hold something against external forces, e.g., gravity.
If you require this option, you have to disable all calls to `self.Ioff`, except the one in `self.shutdown`.

Non-blocking axis movement is provided by a specialized class derived from threading.Thread.

It supports the following general stepping sequences:

normal:
+++++++

    +-----+--+--+--+--+
    | Step|  Channels |
    +=====+==+==+==+==+
    | 1   | 1| 0| 0| 0|
    +-----+--+--+--+--+
    | 2   | 0| 1| 0| 0|
    +-----+--+--+--+--+
    | 3   | 0| 0| 1| 0|
    +-----+--+--+--+--+
    | 4   | 0| 0| 0| 1|
    +-----+--+--+--+--+

highTQ:
+++++++

    +-----+--+--+--+--+
    | Step|  Channels |
    +=====+==+==+==+==+
    | 1   | 1| 1| 0| 0|
    +-----+--+--+--+--+
    | 2   | 0| 1| 1| 0|
    +-----+--+--+--+--+
    | 3   | 0| 0| 1| 1|
    +-----+--+--+--+--+
    | 4   | 1| 0| 0| 1|
    +-----+--+--+--+--+

halfstep:
+++++++++

    +-----+--+--+--+--+
    | Step|  Channels |
    +=====+==+==+==+==+
    | 1   | 1| 1| 0| 0|
    +-----+--+--+--+--+
    | 2   | 0| 1| 0| 0|
    +-----+--+--+--+--+
    | 3   | 0| 1| 1| 0|
    +-----+--+--+--+--+
    | 4   | 0| 0| 1| 0|
    +-----+--+--+--+--+
    | 5   | 0| 0| 1| 1|
    +-----+--+--+--+--+
    | 6   | 0| 0| 0| 1|
    +-----+--+--+--+--+
    | 7   | 1| 0| 0| 1|
    +-----+--+--+--+--+
    | 8   | 1| 0| 0| 0|
    +-----+--+--+--+--+


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
import time
import threading

# hardware io
import PyDAQmx as daq
import ctypes
import numpy as np

# base class
import core.FSRSModule as module


# helper class for stepper motor coil current sequence
class StepSeq():
    def __init__(self, type="normal"):
        if type == "highTQ":
            self.steppattern = [[1, 1, 0, 0],
                                [0, 1, 1, 0],
                                [0, 0, 1, 1],
                                [1, 0, 0, 1]]
            self.Nsteps = 4
        elif type == "halfstep":
            self.steppattern = [[1, 1, 0, 0],
                                [0, 1, 0, 0],
                                [0, 1, 1, 0],
                                [0, 0, 1, 0],
                                [0, 0, 1, 1],
                                [0, 0, 0, 1],
                                [1, 0, 0, 1],
                                [1, 0, 0, 0]]
            self.Nsteps = 8
        else:
            self.steppattern = [[1, 0, 0, 0],
                                [0, 1, 0, 0],
                                [0, 0, 1, 0],
                                [0, 0, 0, 1]]
            self.Nsteps = 4

        self.cstep = 0

    # step in the given direction and return the next step pattern
    def getNextStep(self, dir=1):
        self.cstep = self.cstep + 1 if dir > 0 else self.cstep - 1
        return self.steppattern[self.cstep % self.Nsteps]

    # return the current motor position
    def getCurrentStep(self):
        return self.cstep


# main motor driver class
class NIStepper(module.Axis):
    def __init__(self):
        module.Axis.__init__(self)

        self.name = "NI Stepper Motor Controller"
        self.units2steps = 1.0    #: convert physical units to motor steps (steps / unit)

        # this list is pre-populated as there is no way of actually figuring out whether a motor is connected to a certain port or not..
        self.motors = [{"name": "NI Axis 0",
                        "stepper": StepSeq(type='normal'),
                        "moving": False,
                        "address": "Dev2/port0/line0:3",
                        "delay": 0.002,
                        "target": 0,
                        "thrd": None,
                        "offset": 0,
                        "daq": None},
                       {"name": "NI Axis 1",
                        "stepper": StepSeq(type='normal'),
                        "moving": False,
                        "address": "Dev2/port0/line4:7",
                        "delay": 0.002,
                        "target": 0,
                        "thrd": None,
                        "offset": 4,
                        "daq": None},
                       {"name": "NI Axis 2",
                        "stepper": StepSeq(type='normal'),
                        "moving": False,
                        "address": "Dev2/port1/line0:3",
                        "delay": 0.002,
                        "target": 0,
                        "thrd": None,
                        "offset": 0,
                        "daq": None}]

        # build properties dictionary
        prop = []
        prop.append({'label': 'Axis', 'type': 'choice', 'choices': [m['name'] for m in self.motors], 'value': 0, 'event': "onChangeAxis"})
        prop.append({'label': 'Current Pos', 'type': 'label', 'value': '0'})
        prop.append({'label': 'Target Pos', 'type': 'input', 'value': '0', 'info': 'int', 'event': None})
        prop.append({'label': 'Movement', 'type': 'button', 'value': 'Start', 'event': 'onStartStop'})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)
        self.ready = False

    def initialize(self, others=[]):
        for i, _ in enumerate(self.motors):
            # create NI task
            self.motors[i]["daq"] = daq.Task()
            # assign channels
            self.motors[i]["daq"].CreateDOChan(self.motors[i]["address"], "", daq.DAQmx_Val_ChanForAllLines)
            # set all to False
            self.Ioff(self.motors[i])

    # this function is called when the application is shut down; do all the clean up here (close drivers, etc)
    def shutdown(self):
        # home motors?
        for i, m in enumerate(self.motors):
            self.Ioff(m)

    def Ioff(self, mtr):
        sampsPerChanWritten = daq.int32()
        mtr["daq"].WriteDigitalU8(1, True, 0, daq.DAQmx_Val_GroupByChannel, np.array(0, dtype=daq.uInt8), ctypes.byref(sampsPerChanWritten), None)

    def getCurrentMotor(self):
        return self.motors[self.getPropertyByLabel("axis").getValue()]

    def onChangeAxis(self, event):
        mtr = self.getCurrentMotor()
        self.getPropertyByLabel("current pos").setValue(str(mtr["stepper"].getCurrentStep() / self.units2steps))
        self.getPropertyByLabel("target pos").setValue(str(mtr["target"] / self.units2steps))
        if mtr["moving"]:
            self.getPropertyByLabel("movement").setValue("Stop")
        else:
            self.getPropertyByLabel("movement").setValue("Start")

    def onStartStop(self, event):
        if self.getPropertyByLabel("movement").getValue() == "Start" or not self.getCurrentMotor()["moving"]:
            pos = float(self.getPropertyByLabel("target").getValue())
            self.goto(pos)
        else:
            self.stop()

    # pos is in units
    def updatePosition(self, event=None, pos=None):
        if pos is not None:
            self.getPropertyByLabel("current pos").setValue("%.f" % pos)
        else:
            self.getPropertyByLabel("current pos").setValue("%.f" % self.pos())

    # return current position in units
    def pos(self):
        return self.getCurrentMotor()["stepper"].getCurrentStep() / self.units2steps

    # goto new position - pos is in units
    def goto(self, pos):
        mtr = self.getCurrentMotor()
        mtr["target"] = pos * self.units2steps

        thrd = NIstepperThread(self, mtr)
        mtr["thrd"] = thrd
        thrd.start()

        self.getPropertyByLabel("movement").setValue("Stop")

    def stop(self):
        mtr = self.getCurrentMotor()
        if mtr["thrd"].is_alive():
            mtr["thrd"].stop()

    def onMotorStopped(self, mtr):
        if mtr["thrd"] is not None:
            mtr["thrd"].join()
            mtr["thrd"] = None
        if self.getCurrentMotor()["name"] == mtr["name"]:
            self.getPropertyByLabel("movement").setValue("Start")
            self.updatePosition()
        self.Ioff(mtr)

    # should return True if stage is still moving
    def is_moving(self):
        return self.getCurrentMotor()["moving"]


# ######################################
# helper class for controlling the motor
class NIstepperThread(threading.Thread):
    def __init__(self, parent, motor, **argv):
        threading.Thread.__init__(self)
        self.parent = parent
        self.motor = motor
        self.updDelay = 0.3

        # user stop event, handles also sleep-functionality
        self.canQuit = threading.Event()
        self.canQuit.clear()

    # the main GUI calls this function to terminate the thread
    def stop(self):
        self.canQuit.set()

    # this is the actual thread routine
    def run(self):
        # send started-Event
        self.motor["moving"] = True
        self.motor["target"] = int(self.motor["target"])
        sampsPerChanWritten = daq.int32()

        cpos = self.motor["stepper"].getCurrentStep()
        dir = 1 if self.motor["target"] > cpos else -1
        nexc = time.clock()

        # enter main loop
        while(self.canQuit.isSet() == 0 and self.motor["stepper"].getCurrentStep() != self.motor["target"]):

            # step in given direction
            pattern = self.motor["stepper"].getNextStep(dir)
            out8 = sum(int(j) << (self.motor["offset"] + 3 - i) for i, j in enumerate(pattern) if j)
            writeArray = np.array(out8, dtype=daq.uInt8)

            # send configuration to DAQ
            self.motor["daq"].WriteDigitalU8(1, True, 0, daq.DAQmx_Val_GroupByChannel, writeArray, ctypes.byref(sampsPerChanWritten), None)

            # send position to main GUI
            if nexc < time.clock():
                wx.CallAfter(self.parent.updatePosition, self.motor["stepper"].getCurrentStep())
                nexc = time.clock() + self.updDelay

            # give motor a break
            time.sleep(self.motor["delay"])

        # switch off holding current
        self.motor["daq"].WriteDigitalU8(1, True, 0, daq.DAQmx_Val_GroupByChannel, np.array(0, dtype=daq.uInt8), ctypes.byref(sampsPerChanWritten), None)

        # send terminated-Event
        self.motor["moving"] = False

        wx.CallAfter(self.parent.onMotorStopped, self.motor)
