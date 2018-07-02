"""
.. module: FSRSAcquire
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

FSRSAcquire reads N frames from the camera and displays the results. Supports dT/T, TA and FSRS modes.
Allows to acquire M sets of data. The final result will be the average over the M sets, i.e., effectively NxM frames.
Each set is in addition saved as an individual file.
Data are saved as TAB-delimited three-column ASCII files (A, B, C), where column B is pump-off, C pump-on (or vice versa) and column
A is either B/C, -log10(B/C) or -log(B/C) depending on measurement mode.

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
import os

import core.FSRSModule as module
import core.FSRSPlot as FSRSplot
import core.FSRSutils as cutils


# ##########################################################################################################################
# base class for any experiment
class FSRSAcquire(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "FSRS Acquire"

        # stores the camera module
        self.cameras = []

        # stores the plotting window stuff
        self.plotWnd = None
        self.plotInit = False

        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "Camera", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "Mode", "type": "choice", "choices": ["FSRS", "TA", "T/T0"], "value": 0})
        prop.append({"label": "# of Frames", "type": "spin", "value": 8000, "info": (2, 20000)})
        prop.append({"label": "# of Sets", "type": "spin", "value": 1, "info": (1, 20000)})
        prop.append({"label": "Progress", "type": "progress", "value": 0})
        prop.append({"label": "Save Last", "type": "button", "value": "Save", "event": "onSave"})
        prop.append({"label": "Start", "type": "button", "value": "Acquire", "event": "onStart"})
        self.parsePropertiesDict(prop)

        self.data = np.array([])
        self.intdata = []
        self.N = 1

    def initialize(self, others=[]):
        module.Experiment.initialize(self, others)

        # look for input modules
        self.cameras = []
        ccdchoices = []
        for m in others:
            if m.type == "input" and hasattr(m, "readNframes"):
                self.cameras.append(m)
                ccdchoices.append(str(m.name))
        self.getPropertyByLabel("camera").setChoices(ccdchoices)

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

            # save averaged data
            cutils.saveFSRS(filename, self.data)

            # save intermediate steps
            if len(self.intdata) > 1:
                tmp = filename.split(".")
                if len(tmp) > 1:
                    basename = tmp[:-1].join()
                    ext = "." + tmp[-1]
                else:
                    basename = filename
                    ext = "txt"
                for i in range(len(self.intdata)):
                    cutils.saveFSRS("%s_%d%s" % (basename, i, ext), self.intdata[i])

        dlg.Destroy()

    def onStart(self, event=None):
        if self.running:
            module.Experiment.stop(self)
        else:
            self.N = 0
            self.data = np.array([])
            self.intdata = []

            self.getPropertyByLabel("progress").setValue(0)
            module.Experiment.start(self, AcquireThread, ccd=self.cameras[self.getPropertyByLabel("camera").getValue()], frames=self.getPropertyByLabel("frames").getValue(), sets=self.getPropertyByLabel("sets").getValue())

    def onFinished(self):
        # wait for thread to exit cleanly
        module.Experiment.onFinished(self)

        A, B, C = self.data

        # display results
        plotWnd = FSRSplot.DualPlotFrame(None, title=time.strftime("FSRS Acquire - %H:%M"), size=(800, 600))
        plotWnd.upperPlotCanvas.tightx = True
        plotWnd.lowerPlotCanvas.tightx = True
        plotWnd.lowerPlotCanvas.setXLabel("Wavenumber (px)")
        plotWnd.lowerPlotCanvas.setYLabel("Counts")
        plotWnd.upperPlotCanvas.setYLabel("Gain")
        plotWnd.upperPlotCanvas.addLine(np.arange(len(A)), A)
        plotWnd.lowerPlotCanvas.addLine(np.arange(len(A)), B)
        plotWnd.lowerPlotCanvas.addLine(np.arange(len(A)), C)
        plotWnd.Show()

    def onUpdate(self, val):
        A, B, C = val
        mode = self.getPropertyByLabel("mode").getValue()
        if mode == 0:
            A = -np.log(A)
        elif mode == 1:
            A = -np.log10(A)

        self.intdata.append([A, B, C])

        self.N = self.N + 1
        if self.N == 1:
            self.data = np.array([A, B, C])
        else:
            self.data = self.data + (np.array([A, B, C]) - self.data) / float(self.N)

        self.getPropertyByLabel("progress").setValue((self.N * 100) / self.getPropertyByLabel("sets").getValue())


# ################################################################################
# helper class for experiment providing the actual scan thread
class AcquireThread(module.ExperimentThread):
    def __init__(self, parent, **argv):
        module.ExperimentThread.__init__(self, parent)
        self.ccd = argv['ccd']
        self.frames = argv['frames']
        self.sets = argv['sets']

    # this is the actual scan routine
    def run(self):
        # send started-Event
        wx.CallAfter(self.parent.onStarted)

        # wait 100ms
        time.sleep(0.1)
        cset = 0

        while(self.canQuit.isSet() == 0 and cset < self.sets):
            val = self.ccd.readNframes(self.frames, self.canQuit)
            # send data to main GUI
            wx.CallAfter(self.parent.onUpdate, val)
            cset += 1

        # send terminated-Event
        wx.CallAfter(self.parent.onFinished)
