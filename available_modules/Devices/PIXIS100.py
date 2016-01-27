"""
.. module: PIXIS100
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

Camera module for PrincetonInstrument's PICam compatible cameras.
Currently, only the first attached camera is used.

This module is optimized for a PIXIS100 with a 1340 x 100 pixel sensor chip. If you are using a different camera, you have to go through the code and adapt it where necessary.

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
import numpy as np
import wx
import core.FSRSModule as module
import drivers.picam as picam


class PIXIS100(module.Input):
    def __init__(self):
        module.Input.__init__(self)

        self.name = "PIXIS100"
        self._sWidth = 1340
        self._sHeight = 100

        prop = []
        prop.append({"label": "Camera", "type": "label", "value": ""})
        prop.append({"label": "Temperature", "type": "label", "value": "25"})
        prop.append({"label": "DAQ # of Frames", "type": "spin", "value": 80, "info": (1, 20000)})
        prop.append({"label": "DAQ Band Min.", "type": "spin", "value": 0, "info": (0, self._sWidth - 1)})
        prop.append({"label": "DAQ Band Max.", "type": "spin", "value": self._sWidth, "info": (1, self._sWidth)})
        prop.append({"label": "Flip Phase", "type": "choice", "value": 1, "choices": ["No", "Yes"]})

        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

        # connect to hardware library
        self.cam = picam.picam()

        self.updTimer = wx.Timer()
        self.updTimer.Bind(wx.EVT_TIMER, self.updateTemperature)

    # connect to library
    def initialize(self, others=[]):
        self.cam.loadLibrary()
        self.cam.getAvailableCameras()        # make sure that there is a camera to connect to
        self.cam.connect()

        # get camera model
        id = self.cam.getCurrentCameraID()
        self.getPropertyByLabel("Camera").setValue(picam.PicamModelLookup[id.model])

        # cool down CCD
        self.cam.setParameter("SensorTemperatureSetPoint", -75)
        self.cam.sendConfiguration()

        # shortest expoure
        self.cam.setParameter("ExposureTime", 0)

        # readout mode
        self.cam.setParameter("ReadoutControlMode", picam.PicamReadoutControlMode["FullFrame"])

        # custom chip settings
        self.cam.setParameter("ActiveWidth", self._sWidth)
        self.cam.setParameter("ActiveHeight", self._sHeight)
        self.cam.setParameter("ActiveLeftMargin", 8)         # naming convention is flipped
        self.cam.setParameter("ActiveRightMargin", 8)        # from labView code
        self.cam.setParameter("ActiveTopMargin", 0)         # to current PICam version!!
        self.cam.setParameter("ActiveBottomMargin", 0)        # this makes the DIFFERENCE!!
        self.cam.setParameter("VerticalShiftRate", 3.2)        # select fastest
        self.cam.setROI(0, self._sWidth, 1, 0, self._sHeight, self._sHeight)

        # trigger and timing settings
        self.cam.setParameter("TriggerResponse", picam.PicamTriggerResponse["ReadoutPerTrigger"])
        self.cam.setParameter("TriggerDetermination", picam.PicamTriggerDetermination["PositivePolarity"])

        # set logic out to not ready
        self.cam.setParameter("OutputSignal", picam.PicamOutputSignal["Busy"])

        # shutter delays; open before trigger corresponds to shutter opening pre delay
        self.cam.setParameter("ShutterTimingMode", picam.PicamShutterTimingMode["Normal"])  # OpenBeforeTrigger
        self.cam.setParameter("ShutterClosingDelay", 0)

        # sensor cleaning
        self.cam.setParameter("CleanSectionFinalHeightCount", 1)
        self.cam.setParameter("CleanSectionFinalHeight", self._sHeight)
        self.cam.setParameter("CleanSerialRegister", False)
        self.cam.setParameter("CleanCycleCount", 1)
        self.cam.setParameter("CleanCycleHeight", self._sHeight)
        self.cam.setParameter("CleanUntilTrigger", False)

        # sensor gain settings
        # according to manual, Pixis supports 100kHz and 2MHz; select fastest
        self.cam.setParameter("AdcSpeed", 2.0)
        self.cam.setParameter("AdcAnalogGain", picam.PicamAdcAnalogGain["Low"])
        self.cam.setParameter("AdcQuality", picam.PicamAdcQuality["LowNoise"])
    #    self.cam.setParameter("AdcQuality", picam.PicamAdcQuality["HighCapacity"])

        # send configuration
        self.cam.sendConfiguration()

        # get readout speed
        print "Estimated readout time = %f ms" % self.cam.getParameter("ReadoutTimeCalculation")

        # start timer for reading temperature
        # self.updTimer = threading.Timer(1, self.updateTemperature)
        self.updTimer.Start(1000.0, wx.TIMER_ONE_SHOT)

    # this function is called when the application is shut down; do all the clean up here (close drivers, etc)
    def shutdown(self):
        self.updTimer.Stop()
        self.cam.disconnect()
        self.cam.unloadLibrary()

    def updateTemperature(self, event=None):
        # read temperature and update label
        if self.cam.getParameter("SensorTemperatureStatus") == picam.PicamSensorTemperatureStatus['Locked']:
            T = self.cam.getParameter('SensorTemperatureSetPoint')
            self.getPropertyByLabel("temperature").setValue(str(T) + " - locked")
        else:
            T = self.cam.getParameter("SensorTemperatureReading")
            self.getPropertyByLabel("temperature").setValue(str(T) + " - cooling")
            self.updTimer.Start(1000.0, wx.TIMER_ONE_SHOT)

    # return the band integral over the specified range using column 1
    def read(self):
        c, _, _ = self.readNframes(int(self.getPropertyByLabel("frames").getValue()))

        i1 = int(self.getPropertyByLabel("min").getValue())
        i2 = int(self.getPropertyByLabel("max").getValue())
        if i1 > i2:
            i1, i2 = i2, i1

        return np.sum(c[i2:i1]) / float(i2 - i1)

    # this is the camera function that returns a 3xN array containing the data from the camera driver
    # columns are: col2 / col3, col2, col3
    def readNframes(self, N, canQuit=None):

        # get sensor dimensions
        w, h, _ = self.cam.ROIS[0]
        data = []
        attempt = 0

        # read N frames from the camera and retain only ROI 1
        # the height has been set to 1
        # IMPORTANT: take 20 more frames than specified and discard those after acquisition to get rid of accumulated charge
        # do max 5 attempts before returning an empty list
        while(data == []):
            attempt += 1
            data = self.cam.readNFrames(N + 20)
            if data != []:
                data = np.array(data[0])
                M = data.shape[0]
                if M >= N + 20:
                    data = data.reshape((M, w))
                    data = data[20:, :]
                else:
                    print M
                    data = []

            if canQuit is not None:
                if canQuit.isSet() != 0:
                    return np.array([np.ones(w), np.ones(w), np.ones(w)])

            if attempt > 5:
                return np.array([np.ones(w), np.ones(w), np.ones(w)])

        # get chopped and unchopped
        flip = bool(self.getPropertyByLabel("flip").getValue())
        A = np.flipud(np.nanmean(data[int(not flip)::2, :], axis=0))
        B = np.flipud(np.nanmean(data[int(flip)::2, :], axis=0))
        C = np.nan_to_num(A / B)

        return np.array([C, A, B])
