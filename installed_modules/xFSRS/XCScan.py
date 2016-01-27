"""
.. module:  XCScan
   : platform:  Windows
.. moduleauthor: :  Daniel R. Dietze <daniel.dietze@berkeley.edu>

Measure a 2D contour map consisting of camera signal vs delay time. Can be used to measure Kerr cross-correlation,
TA-maps, FSRS-maps or dT/T-maps. Allows fitting of the data columnwise to a Gaussian to determine probe chirp and IRF.
Data are saved as TAB-delimited (N+1)-column ASCII files (time, N-frequency columns), where the frequency columns
depend on the measurement mode.

..
   This file is part of the pyFSRS app.

   This program is free software:  you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program. If not, see <http: //www.gnu.org/licenses/>.

   Copyright 2014-2016 Daniel Dietze <daniel.dietze@berkeley.edu>.
"""
import wx
import numpy as np
import time
import os

import scipy.optimize as spo
import itertools

import core.FSRSModule as module
import core.FSRSPlot as FSRSplot
import core.FSRSutils as cutils


# ##########################################################################################################################
# base class for any experiment
class XCScan(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "XC Scan"

        # stores the camera module
        self.cameras = []
        self.axes = []
        self.shutters = []

        # stores the 2d data, each column is a new timepoint
        self.data = []
        self.points = []
        self.bg = []

        # stores the plotting window stuff
        self.plotWnd = None
        self.plotInit = False
        self.plotID = 0
        self.running = False

        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "Camera", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "Type", "type": "choice", "choices": ["FSRS", "TA", "T/T0", "Kerr"], "value": 3})
        prop.append({"label": "# of Frames", "type": "spin", "value": 100, "info": (2, 20000)})

        prop.append({"label": "Axis", "type": "choice", "choices": [], "value": 0})
        prop = cutils.appendStageParameters(prop, -300, 300, 20)
        prop.append({"label": "Shutter", "type": "choice", "choices": [], "value": 0})

        prop.append({"label": "Save Last", "type": "button", "value": "Save", "event": "onSave"})

        prop.append({"label": "Progress", "type": "progress", "value": 0})
        prop.append({"label": "Start", "type": "button", "value": "Scan", "event": "onStart"})
        prop.append({"label": "Fit", "type": "button", "value": "Fit", "event": "onFit"})
        self.parsePropertiesDict(prop)
        self.data = np.array([])

    def initialize(self, others=[]):
        module.Experiment.initialize(self, others)

        # look for input modules
        self.cameras = []
        self.axes = []
        self.shutters = []

        axeschoices = []
        ccdchoices = []
        shutterchoices = []

        for m in others:
            if m.type == "input" and hasattr(m, "readNframes"):
                self.cameras.append(m)
                ccdchoices.append(str(m.name))
            if m.type == "output":
                self.shutters.append(m)
                shutterchoices.append(str(m.name))
            if m.type == "axis":
                self.axes.append(m)
                axeschoices.append(str(m.name))
        self.getPropertyByLabel("camera").setChoices(ccdchoices)
        self.getPropertyByLabel("axis").setChoices(axeschoices)
        self.getPropertyByLabel("shutter").setChoices(shutterchoices)

    def onFit(self, event):
        if len(self.data) == 0:
            wx.MessageBox("Nothing to fit yet!", "Fit Last Scan", style=wx.OK)
            return

        gauss = lambda x, y0, A, x0, dx: y0 + A * np.power(16.0, -(x - x0)**2 / dx**2)

        self.getPropertyByLabel("progress").setValue(0)

        x = self.points
        dtmp = self.data.T

        pos = []
        width = []
        i = 0
        errors = False
        for d in dtmp:
            try:
                popt, pcov = spo.curve_fit(gauss, x, d, [d[0], np.amax(d), x[np.argmax(d)], (x[-1] - x[0]) / 5])
                pos.append(popt[2])
                width.append(popt[3])

                i += 1
                self.getPropertyByLabel("progress").setValue(i * 100 / len(dtmp))
            except:
                pos.append(0.0)
                width.append(0.0)
                errors = True
        pos = np.array(pos)
        width = np.array(width)

        self.getPropertyByLabel("progress").setValue(0)

        if errors:
            print "There were errors during the fitting. Could not determine parameters."
        else:
            print "Dispersion: ", np.amax(pos) - np.amin(pos), "fs"
            print "Mean Width: ", np.mean(width), "+-", np.std(width), "fs"

            if np.argmax(pos) - np.argmin(pos) > 0:
                print "You should remove prism from probe."
            else:
                print "You should add prism to probe."

        plframe = FSRSplot.FSRSDualPlotFrame(None, title="Fit Results", size=(640, 480))
        plframe.upperPlotCanvas.setYLabel("Position (fs)")
        plframe.lowerPlotCanvas.setYLabel("Width (fs)")
        plframe.lowerPlotCanvas.setXLabel("Wavelength (px)")
        plframe.upperPlotCanvas.addLine(np.arange(len(pos)), pos)
        plframe.lowerPlotCanvas.addLine(np.arange(len(pos)), width)
        plframe.Show()

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

            cutils.saveXC(filename, self.points, self.data)

        dlg.Destroy()

    def onAxisRangeChange(self, event):
        cutils.onAxisRangeChange(self, event)

    def onStart(self, event=None):
        if self.running:
            module.Experiment.stop(self)

        else:
            if self.plotWnd is not None:
                self.plotWnd.Destroy()
            self.plotInit = False
            self.plotID = 0

            self.plotWnd = FSRSplot.PlotFrame(None, title=time.strftime("XC Scan"), size=(640, 640))
            self.plotWnd.plotCanvas.tightx = True
            self.plotWnd.plotCanvas.tighty = True
            self.plotWnd.Show()

            self.data = []
            self.points = []
            self.bg = []

            s_type = self.getPropertyByLabel("type").getValue()
            s_ccd = self.cameras[self.getPropertyByLabel("camera").getValue()]
            s_axis = self.axes[self.getPropertyByLabel("axis").getValue()]
            s_shutter = self.shutters[self.getPropertyByLabel("shutter").getValue()]
            s_frames = int(self.getPropertyByLabel("frames").getValue())

            self.points = cutils.prepareScanPoints(self)

            self.s_points_iterator = itertools.cycle(self.points)
            self.progress_iterator = itertools.cycle(np.arange(len(self.points) * 1 + 1) * 100 / (len(self.points) * 1))
            self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))

            self.running = True

            module.Experiment.start(self, ScanThread, type=s_type, ccd=s_ccd, axis=s_axis, shutter=s_shutter, frames=s_frames, points=self.points, sets=1)

    def onFinished(self):
        # wait for thread to exit cleanly
        module.Experiment.onFinished(self)
        self.plotWnd = None
        self.plotInit = False
        self.plotID = 0
        self.running = False

    def onUpdate(self, val):
        # prepare data
        A, B, C = val
        mode = self.getPropertyByLabel("type").getValue()
        if mode == 0:
            A = -np.log(A)
        elif mode == 1:
            A = -np.log10(A)

        if mode != 3 or self.bg != []:
            if mode == 3:
                A = 0.5 * (B + C) - self.bg

            if len(self.data) == 0:
                self.data = np.array([A])
            else:
                self.data = np.vstack([self.data, A])

            # update progress bar
            self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))

            # plot in window
            if isinstance(self.plotWnd, wx.Frame):
                if self.plotInit:
                    self.plotWnd.plotCanvas.setImage(self.plotID, np.arange(len(A)), self.points[0: len(self.data)], self.data)
                else:
                    self.plotInit = True
                    self.plotID = self.plotWnd.plotCanvas.addImage(np.arange(len(A)), self.points[0: len(self.data)], self.data)
            else:
                # user closed the plotWindow -> stop thread
                self.onStart()
        else:
            self.bg = 0.5 * (B + C)


# ################################################################################
# helper class for experiment providing the actual scan thread
class ScanThread(module.ExperimentThread):
    def __init__(self, parent, **argv):
        module.ExperimentThread.__init__(self, parent)
        self.ccd = argv['ccd']
        self.frames = argv['frames']
        self.shutter = argv['shutter']
        self.axis = argv['axis']
        self.points = argv['points']
        self.sets = argv['sets']
        self.type = argv['type']

    # this is the actual scan routine
    def run(self):
        # send started-Event
        wx.CallAfter(self.parent.onStarted)

        cset = 0

        # wait 500ms
        time.sleep(0.1)

        # background correction for Kerr
        if self.type == 3:

            # close shutter
            self.shutter.write(0)

            # read background frame
            if self.canQuit.isSet() == 0:
                val = self.ccd.readNframes(self.frames, self.canQuit)

            # send to gui
            wx.CallAfter(self.parent.onUpdate, val)

        # open shutter
        self.shutter.write(1)

        # enter main loop
        while(self.canQuit.isSet() == 0 and cset < self.sets):

            cpoint = 0

            # move to first point
            self.axis.goto(self.points[cpoint])

            while(cpoint < len(self.points) and self.canQuit.isSet() == 0):

                # wait for axis to finish moving
                while self.axis.is_moving() and self.canQuit.isSet() == 0:
                    time.sleep(0.1)

                # read
                if self.canQuit.isSet() == 0:
                    val = self.ccd.readNframes(self.frames, self.canQuit)

                    # send data to main GUI
                    wx.CallAfter(self.parent.onUpdate, val)
                    cpoint += 1

                # move to next point
                self.axis.goto(self.points[cpoint % len(self.points)])

            cset += 1

        # return axis to zero
        self.axis.goto(0.0)

        # close shutter
        self.shutter.write(0)

        # send terminated-Event
        wx.CallAfter(self.parent.onFinished)
