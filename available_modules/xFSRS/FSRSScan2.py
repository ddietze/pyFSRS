"""
.. module: FSRSScan2
   :platform: Windows
.. moduleauthor:: Scott Ellis <skellis@berkeley.edu>

This file belongs in /installed_modules/xFSRS/

FSRSScan2 reads a series of ground state / excited state FSRS spectra. Supports also dT/T, TA and FSRS modes.
Allows to acquire M sets of data. The final result will be the average over the M sets, i.e., effectively NxM frames.
Each set and timestep is saved as an individual file. Data are saved as TAB-delimited three-column ASCII files (A, B, C), where column B is pump-off, C pump-on (or vice versa) and column
A is either B/C, -log10(B/C) or -log(B/C) depending on measurement mode. File names follow the historical Mathies lab convention.

Allows also to simultaneously measure a reference signal, e.g., the actinic pump power from a photodiode using some specified input device.
This reference will be saved individually as a TAB-delimited two-column ASCII file (time, value).

There is a sleep time required for the translation stage to move.
AZ is not supported nor are speeds other than 10 mm/s.

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
"""
import wx
import numpy as np
import time
import os

import itertools

import core.FSRSModule as module
import core.FSRSPlot as FSRSplot
import core.FSRSutils as cutils


# ##########################################################################################################################
# base class for any experiment
class FSRSScan2(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "FSRS Scan 2"

        # stores the camera module
        self.cameras = []
        self.axes = []
        self.shutters = []
        self.inputs = []

        # stores the plotting window stuff
        self.plotWnd = None
        self.plotInit = False

        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "Camera", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "Type", "type": "choice", "choices": ["FSRS", "TA", "T/T0"], "value": 0})
        prop.append({"label": "# of Frames", "type": "spin", "value": 2000, "info": (2, 20000)})

        prop.append({"label": "Axis", "type": "choice", "choices": [], "value": 0})
        prop = cutils.appendStageParameters(prop)    
        prop.append({"label": "Shutter", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "Take Ref.", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "# of Sets", "type": "spin", "value": 1, "info": (1, 1000)})
        prop.append({"label": "Basename", "type": "input", "value": ""})
        prop.append({"label": "Output Path", "type": "file", "value": os.getcwd(), "info": "path"})
        prop.append({"label": "Progress", "type": "progress", "value": 0})
        prop.append({"label": "Status", "type": "label", "value": ""})
        prop.append({"label": "Start", "type": "button", "value": "Scan", "event": "onStart"})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

        self.data = np.array([])
        self.Nsteps = 0
        self.Nsets = 0
  
    def initialize(self, others=[]):
        module.Experiment.initialize(self, others)

        # look for input modules
        self.cameras = []
        self.axes = []
        self.shutters = []
        self.inputs = []

        axeschoices = []
        ccdchoices = []
        shutterchoices = []
        inputchoices = ["No"]

        for m in others:
            if m.type == "input":
                self.inputs.append(m)
                inputchoices.append(str(m.name))
                if hasattr(m, "readNframes"):
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
        self.getPropertyByLabel("take ref.").setChoices(inputchoices)

    def onAxisRangeChange(self, event):
        cutils.onAxisRangeChange(self, event)

    def onStart(self, event=None):
        if self.running:
            module.Experiment.stop(self)
        else:
            if self.plotWnd is not None:
                self.plotWnd.Destroy()
            self.plotInit = False

            self.plotWnd = FSRSplot.DualPlotFrame(None, title=time.strftime("FSRS Scan"), size=(800, 600))
            self.plotWnd.upperPlotCanvas.tightx = True
            self.plotWnd.lowerPlotCanvas.tightx = True
            self.plotWnd.lowerPlotCanvas.setXLabel("Wavenumber (px)")
            self.plotWnd.lowerPlotCanvas.setYLabel("Counts")

            s_type = self.getPropertyByLabel("type").getValue()
            if s_type == 0:
                self.plotWnd.upperPlotCanvas.setYLabel("Gain")
            elif s_type == 1:
                self.plotWnd.upperPlotCanvas.setYLabel("OD")
            else:
                self.plotWnd.upperPlotCanvas.setYLabel("dT / T0")

            self.plotWnd.Show()

            s_ccd = self.cameras[self.getPropertyByLabel("camera").getValue()]
            s_axis = self.axes[self.getPropertyByLabel("axis").getValue()]
            s_shutter = self.shutters[self.getPropertyByLabel("shutter").getValue()]
            s_frames = int(self.getPropertyByLabel("frames").getValue())
            s_ref = self.inputs[self.getPropertyByLabel("take ref.").getValue() - 1] if self.getPropertyByLabel("take ref.").getValue() >= 1 else None

            s_points = cutils.prepareScanPoints(self)
            self.Nsteps = len(s_points) + 1
            s_sets = int(self.getPropertyByLabel("sets").getValue())
            self.Nsets = s_sets

            self.s_points_iterator = itertools.cycle(s_points)
            self.progress_iterator = itertools.cycle(np.linspace(0, 100, len(s_points) * s_sets).astype(int))
            self.getPropertyByLabel("progress").setValue(0)

            self.basename = os.path.join(self.getPropertyByLabel("path").getValue(), self.getPropertyByLabel("basename").getValue())

            # save a timepoints file
            np.savetxt(self.basename + "_timepoints.txt", np.sort(s_points))

            module.Experiment.start(self, ScanThread, type=s_type, ccd=s_ccd, axis=s_axis, shutter=s_shutter, frames=s_frames, points=s_points, sets=s_sets, reference=s_ref)

    def onFinished(self, t=None, r=None):

        # save reference data when required
        if t is not None and r is not None:
            filename = os.path.join(self.getPropertyByLabel("path").getValue(), self.getPropertyByLabel("basename").getValue()) + "_reference.dat"
            data = np.array([t[np.argsort(t)], r[np.argsort(t)]]).T
            np.savetxt(filename, data)

        # wait for thread to exit cleanly
        module.Experiment.onFinished(self)

        # now destroy the plot window
        if isinstance(self.plotWnd, wx.Frame):
            self.plotWnd.Destroy()
        self.plotWnd = None
        self.plotInit = False

    def onUpdate(self, val, grexc, step, set):

        # prepare data
        A, B, C = val
        mode = self.getPropertyByLabel("mode").getValue()
        if mode == 0:
            A = -np.log(A)
        elif mode == 1:
            A = -np.log10(A)

        # save data
        filename = cutils.formatFSRSFilename(mode, self.basename, step, set, grexc)
        cutils.saveFSRS(filename, [A, B, C])

        # update progress bar
        self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))
        self.getPropertyByLabel("status").setValue("position %.0ffs, set %d/%d" % (step, set, self.Nsets))

        # plot in window
        if isinstance(self.plotWnd, wx.Frame):
            if self.plotInit:
                self.plotWnd.upperPlotCanvas.setLine(0, np.arange(len(A)), A)
                self.plotWnd.lowerPlotCanvas.setLine(0, np.arange(len(A)), B)
                self.plotWnd.lowerPlotCanvas.setLine(1, np.arange(len(A)), C)
            else:
                self.plotInit = True
                self.plotWnd.upperPlotCanvas.addLine(np.arange(len(A)), A)
                self.plotWnd.lowerPlotCanvas.addLine(np.arange(len(A)), B)
                self.plotWnd.lowerPlotCanvas.addLine(np.arange(len(A)), C)
        else:
            # user closed the plotWindow -> stop thread
            self.onStart()


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
        self.reference = argv.get('reference', None)
    # this is the actual scan routine
    def run(self):
        # send started-Event
        wx.CallAfter(self.parent.onStarted)
        cset = 0
        reference_data = np.zeros(len(self.points))
        stagerange=1670000. #fs
        maxtranslationTime=30 #seconds measured with a stopwatch for the newmark stages 
        maxinterval=np.amax(self.points)-np.amin(self.points)
        if self.reference is not None and self.reference.hasProperty("wait"):
            old_wait_time = self.reference.getPropertyByLabel("wait").getValue()
            self.reference.getPropertyByLabel("wait").setValue("0")

        # wait 500ms
        time.sleep(0.5)

        if self.type > 0:
            self.shutter.write(1)

        # enter main loop
        while(self.canQuit.isSet() == 0 and cset < self.sets):
            cpoint = 0
            # move to first point
            posx=self.axis.pos()
            currentInterval=abs(self.points[cpoint]-posx)
            self.axis.goto(self.points[cpoint])
            #try to estimate how long translation takes
            time.sleep(0.1+currentInterval/stagerange*maxtranslationTime)

            # use this time to record a ground state spectrum
            # -----------------------------------------------
            if self.type == 0:

                # close shutter
                print "close shutter"
                self.shutter.write(0)
                # record frame
                if self.canQuit.isSet() == 0:
                    val = self.ccd.readNframes(self.frames, self.canQuit)

                    # send to GUI
                    wx.CallAfter(self.parent.onUpdate, val, 0, 0, cset)
                # open shutter
                print "open shutter"
                self.shutter.write(1)
            # record excited state spectra
            # ----------------------------
            while(cpoint < len(self.points) and self.canQuit.isSet() == 0):

                # read
                if self.canQuit.isSet() == 0:
                    val = self.ccd.readNframes(self.frames, self.canQuit)
                    # if user wants some reference signal
                    if self.reference is not None:
                        reference_data[cpoint] = reference_data[cpoint] + self.reference.read()

                    # send data to main GUI
                    wx.CallAfter(self.parent.onUpdate, val, 1, self.points[cpoint], cset)
                    time.sleep(0.2)

                    cpoint += 1

                # move to next point
                currentInterval= abs(self.points[cpoint % len(self.points)]-self.points[cpoint % len(self.points)-1])
                self.axis.goto(self.points[cpoint % len(self.points)])
                time.sleep(0.1+currentInterval/stagerange*maxtranslationTime)
            print "Finished set ", cset
            cset += 1

        # return axis
        self.axis.goto(self.points[0])
        time.sleep(0.1+maxinterval/stagerange*maxtranslationTime)
        # close shutter
        print "close shutter"
        self.shutter.write(0)
        # if reference signal was required
        # restore wait time and send data to main thread
        if self.reference is not None:

            if cset > 0:
                reference_data = reference_data / float(cset)

            if self.reference.hasProperty("wait"):
                self.reference.getPropertyByLabel("wait").setValue(old_wait_time)

            # send terminated-Event
            wx.CallAfter(self.parent.onFinished, self.points, reference_data)

        else:
            wx.CallAfter(self.parent.onFinished)
