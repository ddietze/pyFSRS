"""
.. module: DAQStats
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

DAQStast reads N samples from an input device and displays statistics.
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
class DAQStats(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "DAQ Stats"

        self.daqs = []
        self.data = []
        self.plotWnd = None
        self.plotID = -1

        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "DAQ", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "# of Points", "type": "spin", "info": (1, 100000), "value": 100})
        prop.append({"label": "Progress", "type": "progress", "value": 0})
        prop.append({"label": "Save", "type": "button", "value": "Save Last Scan", "event": "onSave"})
        prop.append({"label": "Start", "type": "button", "value": "Scan", "event": "onStart"})
        self.parsePropertiesDict(prop)

    def initialize(self, others=[]):
        module.Experiment.initialize(self, others)

        # look for input modules
        self.daqs = []
        daqchoices = []
        for m in others:
            if m.type == "input":
                self.daqs.append(m)
                daqchoices.append(str(m.name))
        self.getPropertyByLabel("daq").setChoices(daqchoices)

    def onSave(self, event):
        if len(self.data) == 0:
            wx.MessageBox("Nothing to save yet!", "Save Last Scan", style=wx.OK)
            return

        dlg = wx.FileDialog(None, "Save Last Scan", os.getcwd(), "", "*.*", wx.SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()

            # set new working directory
            directory = os.path.split(filename)
            if not os.path.isdir(filename):
                os.chdir(directory[0])

            cutils.saveFSRS(filename, self.data)

        dlg.Destroy()

    def onStart(self, event=None):
        if self.running:
            module.Experiment.stop(self)
        else:
            self.data = []

            if self.plotWnd is not None:
                self.plotWnd.Destroy()
            self.plotID = -1

            self.plotWnd = FSRSplot.PlotFrame(None, title="DAQ Scan", size=(640, 480))
            self.plotWnd.Show()

            s_daq = self.daqs[self.getPropertyByLabel("daq").getValue()]
            s_points = self.getPropertyByLabel("points").getValue()

            self.progress_iterator = itertools.cycle(np.arange(s_points + 1) * 100 / s_points)
            self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))

            module.Experiment.start(self, DAQStatThread, daq=s_daq, points=s_points)

    def onFinished(self):
        # wait for thread to exit cleanly
        module.Experiment.onFinished(self)

        # detach the plot window
        self.plotWnd = None

        # show stats
        txt = "Mean Value = %g\nStd.Dev = %g" % (np.mean(self.data), np.std(self.data))
        wx.MessageBox(txt, "DAQ Stats", style=wx.OK)

    def onUpdate(self, val):
        self.data = np.append(self.data, val)

        # update progress bar
        self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))

        # update plot
        if isinstance(self.plotWnd, wx.Frame):
            if self.plotID == -1:
                self.plotID = self.plotWnd.plotCanvas.addLine(np.arange(len(self.data)), self.data)
            else:
                self.plotWnd.plotCanvas.setLine(self.plotID, np.arange(len(self.data)), self.data)
        else:
            # user closed the plotWindow -> stop thread
            self.onStart()


# ################################################################################
# helper class for experiment providing the actual scan thread
class DAQStatThread(module.ExperimentThread):
    def __init__(self, parent, **argv):
        module.ExperimentThread.__init__(self, parent)
        self.daq = argv['daq']
        self.points = argv['points']

    # this is the actual scan routine
    def run(self):
        # send started-Event
        wx.CallAfter(self.parent.onStarted)

        # wait 100ms
        time.sleep(0.1)

        cpoint = 0

        # enter main loop
        while(self.canQuit.isSet() == 0 and cpoint < self.points):
            # read value
            val = self.daq.read()

            # send data to main GUI
            wx.CallAfter(self.parent.onUpdate, val)

            cpoint += 1

        # send terminated-Event
        wx.CallAfter(self.parent.onFinished)
