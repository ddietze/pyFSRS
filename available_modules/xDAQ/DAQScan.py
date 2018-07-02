"""
.. module: DAQScan
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

DAQScan provides a module for reading a single value, e.g., from a lock-in, as function of optical delay time (=stage position).
Data may be saved as a TAB-delimited two-column ASCII file (time, value).

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

import numpy as np
import time
import itertools
import os

import core.FSRSModule as module
import core.FSRSPlot as FSRSplot
import core.FSRSutils as cutils


# ##########################################################################################################################
# base class for any experiment
class DAQScan(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "DAQ Scan"

        self.daqs = []

        self.plotWnd = None
        self.plotID = -1

        self.data = []
        self.points = []

        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "DAQ", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "Axis", "type": "choice", "choices": [], "value": 0})
        prop = cutils.appendStageParameters(prop)
        prop.append({"label": "Save Scan", "type": "button", "value": "Save", "event": "onSave"})
        prop.append({"label": "Progress", "type": "progress", "value": 0})
        prop.append({"label": "Start", "type": "button", "value": "Scan", "event": "onStart"})
        self.parsePropertiesDict(prop)

    def initialize(self, others=[]):
        module.Experiment.initialize(self, others)

        # look for input modules
        self.daqs = []
        daqchoices = []
        self.axes = []
        axeschoices = []
        for m in others:
            if m.type == "input":
                self.daqs.append(m)
                daqchoices.append(str(m.name))
            if m.type == "axis":
                self.axes.append(m)
                axeschoices.append(str(m.name))
        self.getPropertyByLabel("daq").setChoices(daqchoices)
        self.getPropertyByLabel("axis").setChoices(axeschoices)

    def onAxisRangeChange(self, event):
        cutils.onAxisRangeChange(self, event)

    def onSave(self, event):
        if len(self.data) == 0:
            wx.MessageBox("Nothing to save yet!", "Save Last Scan", style=wx.OK)
            return

        dlg = wx.FileDialog(None, "Save Last Scan", os.getcwd(), "", "*.*", wx.FD_SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()

            # set new working directory
            directory = os.path.split(filename)
            if not os.path.isdir(filename):
                os.chdir(directory[0])

            ind = np.argsort(self.points)
            cutils.saveFSRS(filename, [self.points[ind], self.data[ind]])

        dlg.Destroy()

    def onStart(self, event=None):
        if self.running:
            module.Experiment.stop(self)
        else:
            self.data = []
            self.points = []

            if self.plotWnd is not None:
                self.plotWnd.Destroy()
            self.plotID = -1

            self.plotWnd = FSRSplot.PlotFrame(None, title="DAQScan", size=(640, 480))
            self.plotWnd.Show()

            s_axis = self.axes[self.getPropertyByLabel("axis").getValue()]
            s_daq = self.daqs[self.getPropertyByLabel("daq").getValue()]
            self.points = cutils.prepareScanPoints(self)

            self.progress_iterator = itertools.cycle(np.arange(len(self.points) + 1) * 100 / (len(self.points)))
            self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))

            module.Experiment.start(self, DAQScanThread, daq=s_daq, axis=s_axis, points=self.points)

    def onFinished(self):
        # wait for thread to exit cleanly
        module.Experiment.onFinished(self)

        # detach the plot window
        self.plotWnd = None

    def onUpdate(self, val):
        self.data = np.append(self.data, val)

        # update progress bar
        self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))

        # update plot
        if isinstance(self.plotWnd, wx.Frame):
            if self.getPropertyByLabel('random'):
                ind = np.argsort(self.points[:len(self.data)])
                x = self.points[:len(self.data)][ind]
                y = self.data[ind]
            else:
                x = self.points[:len(self.data)]
                y = self.data
            if self.plotID == -1:
                self.plotID = self.plotWnd.plotCanvas.addLine(x, y)
            else:
                self.plotWnd.plotCanvas.setLine(self.plotID, x, y)
        else:
            # user closed the plotWindow -> stop thread
            self.onStart()


# ################################################################################
# helper class for experiment providing the actual scan thread
class DAQScanThread(module.ExperimentThread):
    def __init__(self, parent, **argv):
        module.ExperimentThread.__init__(self, parent)
        self.daq = argv['daq']
        self.axis = argv['axis']
        self.points = argv['points']

    # this is the actual scan routine
    def run(self):
        # send started-Event
        wx.CallAfter(self.parent.onStarted)

        # wait 500ms
        time.sleep(0.1)

        cpoint = 0

        # enter main loop
        while(self.canQuit.isSet() == 0 and cpoint < len(self.points)):

            # move to first point
            self.axis.goto(self.points[cpoint])

            # wait for axis to finish moving
            while self.axis.is_moving() and self.canQuit.isSet() == 0:
                time.sleep(0.01)

            val = self.daq.read()

            # send data to main GUI
            wx.CallAfter(self.parent.onUpdate, val)

            cpoint += 1

        self.axis.goto(self.points[0])

        # send terminated-Event
        wx.CallAfter(self.parent.onFinished)
