"""
.. module: DAQMonitor
   :platform: Windows
.. moduleauthor:: Scott R Ellis <skellis@berkeley.edu>

DAQMonitor reads N samples from an input device and displays statistics.\
If the measurement is outside of a tolerance threshold (standard deviations) it faults.
You can report the fault by sending an email and/or by logging it in a faultLog.txt
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
from time import gmtime, strftime
import itertools
import os
import smtplib
#import shutil

import core.FSRSModule as module
import core.FSRSPlot as FSRSplot
import core.FSRSutils as cutils
senderEmail=""
password=""
destinationEmail=""
duration=[]
tolerance=[]

def sendEmail(senderEmail,password,destinationEmail,duration,tolerance):
#Create a catalogue of smtp names and ports
    print "loc 2"
    if "gmail" in senderEmail:
        hostName='smtp.gmail.com'
        portNum=587
    elif "yahoo" in senderEmail:
        hostName='smtp.mail.yahoo.com'
        portNum=465
    elif "microsoft" in senderEmail:
        hostName='smtp.office365.com'
        portNum=587
    else:
        print "can't identify port number or host name for given senderEmail. Please look it up and enter it manually into the code"
        return
    
    s = smtplib.SMTP(host=hostName, port=portNum)
    s.starttls()
    s.login(senderEmail, password)
    subject = "Instrument Fault Alert pyFSRS"
    text = "This is an automated alter from pyFSRS. The instrument is unstable.\n An average over {} measurements have fell outside a tolerance of {} standard deviations.\nHave a great day!".format(str(duration),str(tolerance))
    message = 'Subject: {}\n\n{}'.format(subject, text)
    s.sendmail(senderEmail,destinationEmail,message)
    # Terminate the SMTP session and close the connection
    s.quit()
    return

# ##########################################################################################################################
# base class for any experiment

class DAQMonitor(module.Experiment):
    def __init__(self):
        module.Experiment.__init__(self)

        self.name = "DAQ Monitor"

        self.daqs = []
        self.data = []
        self.slidingAvg=[]
        self.plotWnd = None
        self.plotID = -1

        # when creating the properties, you should create a start/stop button with the label "Start"
        prop = []
        prop.append({"label": "DAQ", "type": "choice", "choices": [], "value": 0})
        prop.append({"label": "# of Points", "type": "spin", "info": (1, 1000000), "value": 200})
        prop.append({"label": "Progress", "type": "progress", "value": 0})
        prop.append({"label": "Start", "type": "button", "value": "Scan", "event": "onStart"})
        prop.append({"label": "Save", "type": "button", "value": "Save Last Scan", "event": "onSave"})
        prop.append({"label": "Tolerance (std dev)", "type":  "input", "value": ".1"})
        prop.append({"label": "Average Duration", "type": "spin", "info": (1, 100000), "value": 10})
        prop.append({"label": "Status", "type": "label", "value": "Stable"})
        prop.append({"label": "Send Email at Fault", "type": "checkbox", "value": 0, "info": "send email at initial fault"})
        prop.append({"label": "Outgoing Email Address", "type": "input", "value": "test@gmail.com"})
        prop.append({"label": "Password", "type": "input", "value": "testpassword123"})
        prop.append({"label": "Destination Email", "type": "input", "value": "test@gmail.com"})
        prop.append({"label": "Path", "type": "file", "value": os.getcwd(), "info": "path"})
        prop.append({"label": "Keep Fault Log", "type": "checkbox", "value": 0, "info": "generate faultLog.txt"})
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

        dlg = wx.FileDialog(None, "Save Last Scan", os.getcwd(), "", "*.*", wx.FD_SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetPath()

            # set new working directory
            directory = os.path.split(filename)
            if not os.path.isdir(filename):
                os.chdir(directory[0])

            cutils.saveFSRS(filename, self.data)

        dlg.Destroy()

    def onStart(self, event=None):
        if self.getPropertyByLabel("Keep Fault Log").getValue():
            logname = os.path.join(self.getPropertyByLabel("Path").getValue(),"faultLog.txt")
            flog = open("faultLog.txt","a")
            flog.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+" - log in\n{}measurements will be made.\nDuration = {}, Tolerance = {}\nTime of Fault\tCurrent Value\tCurrent Mean\tCurrent stdev\n".format(self.getPropertyByLabel("# of Points").getValue(),self.getPropertyByLabel("Average Duration").getValue(),self.getPropertyByLabel("Tolerance (std dev)").getValue()))
            flog.close()
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

            module.Experiment.start(self, DAQMonitorThread, daq=s_daq, points=s_points)

    def onFinished(self):
        # wait for thread to exit cleanly
        module.Experiment.onFinished(self)

        # detach the plot window
        self.plotWnd = None

        # show stats
        txt = "Mean Value = %g\nStd.Dev = %g" % (np.mean(self.data), np.std(self.data))
        wx.MessageBox(txt, "DAQ Monitor", style=wx.OK)

    def onUpdate(self, val):
        self.data = np.append(self.data, val)
        duration=int(self.getPropertyByLabel("Average Duration").getValue())
        #check the stability once in a while

        #check stability ever 'duration' measurments after we've acquired 95 measurements so that we have reasonable statistics
        if (len(self.data)+1)%duration==0 and len(self.data)>95:
            slidingAvg=np.mean(self.data[-duration-1:-1])
            netAvg=np.mean(self.data)
            stDev0=np.std(self.data)
            tolerance=float(self.getPropertyByLabel("Tolerance (std dev)").getValue())
            if np.absolute((slidingAvg-netAvg)/(stDev0*tolerance))>1:
                if self.getPropertyByLabel("Keep Fault Log").getValue():
                    logname = os.path.join(self.getPropertyByLabel("Path").getValue(),"faultLog.txt")
                    flog = open("faultLog.txt","a")
                    flog.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+"\t{}\t{}\t{}\n".format(str(slidingAvg),str(netAvg),str(stDev0)))
                    flog.close()
                if self.getPropertyByLabel("Status").getValue()=="Stable":
                    print "Instability Fault. Duration = {}\tTolerance set to {} standard deviations".format(str(duration),str(tolerance))
                    self.getPropertyByLabel("Status").setValue("Unstable")
                    if self.getPropertyByLabel("Send Email at Fault").getValue()==1:
                        print "loc 1"
                        destinationEmail=self.getPropertyByLabel("Destination Email").getValue()
                        password=self.getPropertyByLabel("Password").getValue()
                        senderEmail=self.getPropertyByLabel("Outgoing Email Address").getValue()
                        sendEmail(senderEmail,password,destinationEmail,duration,tolerance)

                
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
class DAQMonitorThread(module.ExperimentThread):
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
