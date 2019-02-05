"""
.. module: GridOptimize2D
   :platform: Windows
.. moduleauthor::Scott R. Ellis <skellis@berkeley.edu>

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
import core.OptPlot as OptPlot
import core.Optutils as outils
# ##########################################################################################################################
# base class for any experiment
class GridOptimize2D(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "Grid Optimize 2D"
        self.dim=2
        self.daqs = []

        self.plotWnd = None
        self.plotID = -1

        self.data = np.array([], dtype=np.float64).reshape(0,self.dim+1)
        self.domain=np.zeros((2,self.dim))
        self.domain0=np.zeros((2,self.dim))
        self.gridtype=0
        self.convpower=2
        self.num=[]
        self.x0=np.zeros((self.dim))
        self.e=[]
        self.og=[]
        self.oi=[]
        self.fog=[]
        self.gfog=[]
        self.hfog=[]
        self.ifog=[]
        self.ftemp=float('Inf')
        self.fmin=float('Inf')
        self.cset=0
        self.cpoint=0
        self.numpnts=0
        self.maxiter=20
        self.xtol=1
        self.fatol=1
        self.minloc=np.array([], dtype=np.float64).reshape(0,self.dim)
        self.grid=np.array([], dtype=np.float64).reshape(0,self.dim)
        self.gridindex=np.array([], dtype=np.float64).reshape(0,self.dim)
        self.coordlist=np.array([], dtype=np.float64).reshape(0,self.dim+1)
        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "DAQ", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "Convergence Power", "type":  "input", "value": "2"})
        prop.append({"label": "Function Tolerance", "type":  "input", "value": "0.03"})
        prop.append({"label": "Parameter Tolerance", "type":  "input", "value": "0.1"})
        prop.append({"label": "Max Iterations", "type":  "input", "value": "20"})
        prop.append({"label": "Grid Type", "type": "choice", "value": 0, "choices": ["linear", "antigauspace","erfspace"], "event": None})
        for i in range(1,self.dim+1):
            prop = outils.appendStageParameters(prop,index=i)
        #prop = outils.appendStageParameters(prop,index=2)
        prop.append({"label": "Random", "type": "checkbox", "value": 0, "info": "randomize search","event": "onRandomize"})
        # prop.append({"label": "Use File", "type": "file", "value": "", "info": "open"})
        # prop.append({"label": "Save Scan", "type": "button", "value": "Save", "event": "onSave"})
        prop.append({"label": "Basename", "type": "input", "value": ""})
        prop.append({"label": "Output Path", "type": "file", "value": os.getcwd(), "info": "path"})
        prop.append({"label": "Progress", "type": "progress", "value": 0})
        prop.append({"label": "Start", "type": "button", "value": "Scan", "event": "onStart"})
        self.parsePropertiesDict(prop)

    def initialize(self, others=[]):
        module.Experiment.initialize(self, others)
        # look for input modules
        self.daqs = []
        daqchoices = []
        self.valves = []
        valveschoices = []
        for m in others:
            if m.type == "input":
                self.daqs.append(m)
                daqchoices.append(str(m.name))
            if m.type == "valve":
                self.valves.append(m)
                valveschoices.append(str(m.name))
        self.getPropertyByLabel("daq").setChoices(daqchoices)
        for i in range(1,self.dim+1):
            self.getPropertyByLabel("Valve "+str(i)).setChoices(valveschoices)
        #self.getPropertyByLabel("Valve 2").setChoices(valveschoices)

    def onRandomize(self, event):
        outils.onRandomize(self, event)


    def onStart(self, event=None):
        if self.running:
            module.Experiment.stop(self)
        else:
            self.data = np.array([], dtype=np.float64).reshape(0,self.dim+1)
            if self.plotWnd is not None:
                self.plotWnd.Destroy()
            self.plotID = -1

            self.plotWnd = OptPlot.PlotFrame(None, title="Grid Search", size=(640, 480))
            self.plotWnd.Show()

            s_valve1 = self.valves[self.getPropertyByLabel("Valve 1").getValue()]
            s_valve2 = self.valves[self.getPropertyByLabel("Valve 2").getValue()]
            s_daq = self.daqs[self.getPropertyByLabel("daq").getValue()]
            s_random = self.getPropertyByLabel("Random").getValue()
            self.convpower=self.getPropertyByLabel("Convergence Power").getValue()
            self.gridtype=self.getPropertyByLabel("Grid Type").getValue()
            self.maxiter=float(self.getPropertyByLabel("Max Iterations").getValue())
            self.xtol=float(self.getPropertyByLabel("Parameter Tolerance").getValue())
            self.fatol=float(self.getPropertyByLabel("Function Tolerance").getValue())
            self.domain= outils.prepareDomain(self)
            self.domain0=self.domain

            if s_random==False:
                self.x0= outils.preparex0(self)
            else:
                self.x0=np.zeros((self.dim))

            self.num= outils.preparenum(self)
            self.numpnts =1

            for i in range(len(self.num)):
                self.numpnts*=self.num[i]

            self.grid,self.gridindex=outils.prepareGridPoints(self)
            self.e=np.vstack((self.grid,self.gridindex))
            self.og,self.oi=outils.distcoordsort(self.e,self.x0)
            self.progress_iterator = itertools.cycle(np.arange(self.numpnts + 1) * 100 / (self.numpnts))
            self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))


            module.Experiment.start(self, GridSearchThread, daq=s_daq, valve1=s_valve1,valve2=s_valve2, 
            grid=self.og,x0=self.x0,domain=self.domain,num=self.num,gridtype=self.gridtype,convpower=self.convpower,
            maxiter=self.maxiter,fatol=self.fatol,xtol=self.xtol,random=s_random)

    def onFinished(self,coordlist):
        # wait for thread to exit cleanly
        x = self.data[self.data[:,-1].argsort()][0,0]
        y = self.data[self.data[:,-1].argsort()][0,1]
        z = self.data[self.data[:,-1].argsort()][0,2]
        self.plotID = self.plotWnd.plotCanvas.addScatter(x,y, self.domain0)
        #self.plotWnd.plotCanvas.setScatter(self.plotID,x, y,self.domain0)
        module.Experiment.onFinished(self)
        self.getPropertyByLabel("progress").setValue(100)
        if self.getPropertyByLabel("Basename").getValue()=='':
            basename="alpha0"
        else:
            basename =self.getPropertyByLabel("Basename").getValue()
        logname = os.path.join(self.getPropertyByLabel("Output Path").getValue(),basename+".txt")
        np.savetxt(logname, coordlist, delimiter='\t')
        self.plotWnd = None

    def onUpdate(self, xpoint,ypoint,val,cset,cpoint):
        self.data= np.vstack((self.data, np.array([xpoint,ypoint,val])))
        # update progress bar
        self.getPropertyByLabel("progress").setValue(next(self.progress_iterator))
        # update plot
        if isinstance(self.plotWnd, wx.Frame):
            x = self.data[self.numpnts*cset:-1,0]
            y = self.data[self.numpnts*cset:-1,1]
            if self.plotID == -1:
                self.plotID = self.plotWnd.plotCanvas.addScatter(x, y,self.domain0)
            if cpoint==0 and cset!=0:
                self.plotID = self.plotWnd.plotCanvas.addScatter(x, y,self.domain0)
            else:
                self.plotWnd.plotCanvas.setScatter(cset, x, y,self.domain0)
        else:
            self.onStart()


# ################################################################################
# helper class for experiment providing the actual scan thread
class GridSearchThread(module.ExperimentThread):
    def __init__(self, parent, **argv):
        module.ExperimentThread.__init__(self, parent)
        self.daq = argv['daq']
        self.valve1 = argv['valve1']
        self.valve2 = argv['valve2']
        self.grid = argv['grid']
        self.x0=argv['x0']
        self.domain=argv['domain']
        self.num=argv['num']
        self.gridtype=argv['gridtype']
        self.convpower=argv['convpower']
        self.maxiter=argv['maxiter']
        self.fatol=argv['fatol']
        self.xtol=argv['xtol']
        self.random=argv['random']
    # this is the actual scan routine
    def run(self):
        # send started-Event
        wx.CallAfter(self.parent.onStarted)
        # wait 100ms
        time.sleep(0.1)
        dim=len(self.x0)
        self.cpoint = 0
        self.cset = 0
        ftemp=float('Inf')
        fmin=float('Inf')
        scale=np.full(dim,1/float(self.convpower))
        coordlist=np.array([], dtype=np.int64).reshape(0,dim+1)
        # enter main loop
        while(self.cset < self.maxiter):
            grid,gridindex=outils.prepareGridPoints(self)
            e=np.vstack((grid,gridindex))
            if self.random==True:
                orderedgrid,orderedindex=outils.randomcoordsort(e)
            else:
                orderedgrid,orderedindex=outils.distcoordsort(e,self.x0)
            fog=np.array([], dtype=np.int64).reshape(0,2*dim+1)
            self.cpoint = 0
            while(self.canQuit.isSet() == 0 and self.cpoint < np.shape(orderedgrid)[0]):

                # move to first point
                self.valve1.goto(orderedgrid[self.cpoint,0])
                self.valve2.goto(orderedgrid[self.cpoint,1])
                # wait for valve to finish moving
                while self.valve1.is_moving() or self.valve2.is_moving() and self.canQuit.isSet() == 0:
                    time.sleep(0.01)

                val = self.daq.read(orderedgrid[self.cpoint,:])
                # send data to main GUI
                wx.CallAfter(self.parent.onUpdate,orderedgrid[self.cpoint,0],orderedgrid[self.cpoint,1], val,self.cset,self.cpoint)
                fcur=np.array([orderedgrid[self.cpoint,0],orderedgrid[self.cpoint,1],orderedindex[self.cpoint,0],orderedindex[self.cpoint,1],val])
                fog=np.vstack(([orderedgrid[self.cpoint,0],orderedgrid[self.cpoint,1],orderedindex[self.cpoint,0],orderedindex[self.cpoint,1],val],fog))
                self.cpoint += 1
            gfog=fog[fog[:,-1].argsort()]
            hfog=np.delete(gfog,[range(dim,2*dim)],axis=1)
            coordlist=np.vstack((hfog,coordlist))
            ftemp=gfog[0,-1]
            minloc=gfog[0,0:dim]
            minindex=gfog[0,dim:2*dim]
            self.x0=minloc
            #calculate the largest domain for comparison with xtol
            xtemp=np.amax(self.domain[:,1]-self.domain[:,0])
            if 1:
                print "_________________Grid Iteration: ", self.cset+1,"___________________"
                print "Grid Domain: " ,self.domain
                print "Old value: ", fmin, "New Value:" ,ftemp
                print "Minimum location: ",minloc
                print "Minimum index: ",minindex
                print "Change: " ,fmin-ftemp
            if ftemp>fmin or ftemp<fmin-self.fatol:
                self.domain=outils.reducedomain(self.domain,x0=self.x0,scale =scale)
            elif abs(fmin-ftemp)<=float(self.fatol) and ftemp<=fmin:
                break
            #instrument precision is met
            elif xtemp<float(self.xtol):
                break
            self.cset += 1
            fmin=ftemp
        self.valve1.goto(0)
        self.valve2.goto(0)

        # send terminated-Event
        wx.CallAfter(self.parent.onFinished,coordlist)
