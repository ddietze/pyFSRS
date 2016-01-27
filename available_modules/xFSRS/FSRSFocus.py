"""
.. module: FSRSFocus
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

FSRSFocus reads N frames from the camera and displays the results as a live stream. Great for alignment purposes. Supports dT/T, TA and FSRS modes.
Data cannot be saved, use 'FSRSAcquire' or 'FSFSScan' instead.

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

import core.FSRSModule as module
import core.FSRSPlot as FSRSplot


# ##########################################################################################################################
# base class for any experiment
class FSRSFocus(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "FSRS Focus"

        # stores the camera module
        self.cameras = []

        # stores the plotting window stuff
        self.plotWnd = None
        self.plotInit = False

        self.running = False
        self.data = None

        self.updTimer = wx.Timer()
        self.updTimer.Bind(wx.EVT_TIMER, self.updateDisplay)

        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "Camera", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "Mode", "type": "choice", "choices": ["FSRS", "TA", "T/T0"], "value": 0})
        prop.append({"label": "# of Frames", "type": "spin", "value": 80, "info": (2, 20000)})
        prop.append({"label": "Start", "type": "button", "value": "START", "event": "onStart"})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

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

    def onStart(self, event=None):
        if self.plotWnd is not None:
            self.plotWnd.Destroy()
            self.plotWnd = None
            self.plotInit = False
        if self.running:
            self.running = False
            self.updTimer.Stop()
            module.Experiment.stop(self)
        else:
            self.plotWnd = FSRSplot.DualPlotFrame(None, title="FSRS Focus", size=(800, 600))
            self.plotWnd.upperPlotCanvas.tightx = True
            self.plotWnd.lowerPlotCanvas.tightx = True
            self.plotWnd.lowerPlotCanvas.setXLabel("Wavenumber (px)")
            self.plotWnd.lowerPlotCanvas.setYLabel("Counts")
            self.plotWnd.upperPlotCanvas.setYLabel("Gain")
            self.plotWnd.Show()

            self.running = True
            self.updTimer.Start(200.0, wx.TIMER_ONE_SHOT)

            module.Experiment.start(self, FocusThread, ccd=self.cameras[self.getPropertyByLabel("camera").getValue()], frames=self.getPropertyByLabel("frames").getValue())

    def onFinished(self):
        # wait for thread to exit cleanly
        module.Experiment.onFinished(self)

        # now destroy the plot window
        if isinstance(self.plotWnd, wx.Frame):
            self.plotWnd.Destroy()
        self.plotWnd = None
        self.plotInit = False

    def onUpdate(self, val):
        try:
            A, B, C = val
            mode = self.getPropertyByLabel("mode").getValue()
            if mode == 0:
                A = -np.log(A)
            elif mode == 1:
                A = -np.log10(A)
            self.data = (A, B, C)
        except:
            pass

    def updateDisplay(self,event=None):
        event.Skip()
        if self.data is None:
            self.updTimer.Start(200.0, wx.TIMER_ONE_SHOT)
            return

        A, B, C = self.data
        x = np.arange(len(A))
        if isinstance(self.plotWnd, wx.Frame):
            if self.plotInit:
                self.plotWnd.upperPlotCanvas.setLine(0, x, A)
                self.plotWnd.lowerPlotCanvas.setLine(0, x, B)
                self.plotWnd.lowerPlotCanvas.setLine(1, x, C)
            else:
                self.plotInit = True
                self.plotWnd.upperPlotCanvas.addLine(x, A)
                self.plotWnd.lowerPlotCanvas.addLine(x, B)
                self.plotWnd.lowerPlotCanvas.addLine(x, C)

            wx.GetApp().Yield()
            self.updTimer.Start(0.2, wx.TIMER_ONE_SHOT)
        elif self.running:
            # user closed the plotWindow -> stop thread
            self.plotWnd = None
            self.plotInit = False
            self.onStart()

# ################################################################################
# helper class for experiment providing the actual scan thread
class FocusThread(module.ExperimentThread):
    def __init__(self, parent, **argv):
        module.ExperimentThread.__init__(self, parent)
        self.ccd = argv['ccd']
        self.frames = argv['frames']

    # this is the actual scan routine
    def run(self):
        # send started-Event
        wx.CallAfter(self.parent.onStarted)

        # wait 500ms
        time.sleep(0.1)

        # enter main loop
        while(self.canQuit.isSet() == 0):

            #while 1:
            val = self.ccd.readNframes(self.frames, self.canQuit)
            #    if val != []:
            #        break

            # send data to main GUI
            wx.CallAfter(self.parent.onUpdate, val)

            time.sleep(0.05)

        # send terminated-Event
        wx.CallAfter(self.parent.onFinished)
