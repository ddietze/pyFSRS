"""
.. module: NewmarkStage
   :platform: Windows
.. moduleauthor:: Scott R. Ellis <skellis@berkeley.edu>

NewmarkStage.py is a module for controlling a 3 axis motion controller.

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
# base class
import core.FSRSModule as module
import visa
import numpy as np
import wx
import time
from time import gmtime, strftime
import threading
import serial
import unicodedata
import os
readString="oregon"
writeString ="WQ;WY;"

def plugAndPlayComPorts(writeString,readString,skp=0,timeoutx=0.1,baudratex=9600,readbytes=100000):
  counter=0
  comPortNames=""
  desiredName=""
  desiredOutput=""
  found=0
  rm = visa.ResourceManager()
  comres = rm.list_resources(query=u'ASRL?*')
  print comres
  comres_info = rm.list_resources_info()
  for d in comres:
    tempUnicodePort= comres_info[d].alias
    tempPortName=unicodedata.normalize('NFKD', tempUnicodePort).encode('ascii','ignore')
    comPortNames+=tempPortName+";"
    counter+=1
    ser = serial.Serial()
    ser.port= tempPortName
    ser.timeout=timeoutx
    ser.baudrate=baudratex
    ser.open()
    ser.write(writeString)
    ser.flush
    output=ser.read(readbytes).lower()
    ser.close()
    if output.find(readString) != -1:
      found = 1
      desiredOutput=output
      desiredPort=d
      desiredName=tempPortName
  print str(counter)+" Com ports were detected."
  if counter>0:
    print comPortNames
    if found:
      print "Instrument returned: "+desiredOutput
      print "Instrument automatically connected at "+desiredName  
      if counter > skp:
        return desiredPort,desiredName
    else:
      print "The port you were looking for was not found. You could consider changing the number of bites read, the default baud rate or the serial time out."
  return ""

class NewmarkStage(module.Axis):
    """A prototype for an axis module for pyFSRS.
    """
    def __init__(self):
        module.Axis.__init__(self)

        self.name = "Newmark Stage"
        self.fs2mm = 2.9979e8 * 1e3 * 1e-15 / 2   #: mm stage travel / fs delay
        #Measured with ruler self.steps2mm=31952.5 steps to one mm but you might be changed this if for example axis Z were used in degrees or rad
        self.steps2mm=31952.5

        self.steps2degrees=84000000. #Still needs to be finely calibrated
        self.home = -0.0                       #: homing position = most negative position allowed
        self.motors = ["AY","AZ"]            #: note AZ is 
        #self.motors = ["AX"]
        self.speeds=["10","5","2","1","2000","5000","10000","20000","50000","100000"]
        # build properties dictionary
        prop = []
        
        prop.append({'label': 'Axis', 'type': 'choice', 'choices': self.motors, 'value': 0, 'event': None})
        prop.append({"label": 'Speed (mm/s and mm/s^2)', 'type': 'choice', 'value': 0, 'choices': self.speeds, "event": None})
        prop.append({'label': 'Target (fs)', 'type': 'input', 'value': '0', 'info': 'int', 'event': None})
        prop.append({'label': 'Movement', 'type': 'button', 'value': 'Start', 'event': 'onStartStop'})
        prop.append({'label': 'Home (fs)', 'type': 'label', 'value': str(self.home), 'event': None})
        prop.append({'label': 'Current Position (fs)', 'type': 'label', 'value': '0.0'})
        prop.append({'label': 'Address:', 'type': 'label', 'value': '', 'event': None})
        prop.append({'label': 'Range (fs)', 'type': 'label', 'value': '1670000'})
        prop.append({"label": "Keep Log", "type": "checkbox", "value": 0, "info": "generate positionLog.txt"})
        prop.append({"label": "Log Path", "type": "file", "value": os.getcwd(), "info": "path"})
        prop.append({'label': 'Warning:', 'type': 'label', 'value': 'When pyFSRS freezes the t0 position will be lost. It is recommended that you generate a position log so that t0 may be recovered.'})
        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

    def initialize(self, others=[]):
        count = module.Axis.initialize(self, others)
        adr,adrName = plugAndPlayComPorts(writeString,readString)
        self.getPropertyByLabel("address").setValue(adr)
        self.getPropertyByLabel("address").setLabel(adrName)
        self.connect()
        #self.getPropertyByLabel("axis").setValue("#" + str(count + 1))

    def shutdown(self):
        try:
            self.updTimer.cancel()
        except:
            pass
        self.disconnect()

    # establish / end a pyVISA connection
    def connect(self, event=None):
        adr = self.getPropertyByLabel("address").getValue()
        adrName= self.getPropertyByLabel("address").getLabel()
        if not adr:
            self.ready = False
            return
        self.ser = serial.Serial()
        self.ser.port= adrName
        self.ser.timeout=.06
        self.ser.baudrate=9600
        self.readbytes=100
        tempstatus=""
        inmotion=False
        self.ser.open()
        self.ser.write("WY;")
        #check to makesure you're connected
        ID = self.ser.read(self.readbytes).lower()
        if ID.find("oregon") == -1:
             raise ValueError("Cannot connect to Newmark Motion Controller at address %s. ID says %s." % (adr, ID))
        # get available motors and update list

        self.getPropertyByLabel("axis").setChoices(self.motors)

        # reset controller to default values set the baudrate to 9600 and set the units to approximately mm
        self.ser.write("RS;")
        time.sleep(2)
        self.ser.write("SB9600;")
        tempstatus=self.ser.read(self.readbytes).lower()
        while not tempstatus=="":
            tempstatus=self.ser.read(self.readbytes).lower()
        if self.getPropertyByLabel("Keep Log").getValue():
            log = open("positionLog.txt","a")
            log.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+" - log in\n")
            log.close()
        # set units to MM
        # set the acceleration and velocity in mm/s and mm/s^2 and move to 0 fs
        for m in self.motors:
            if m=="AX" or m=="AY":
                self.ser.write("%s;UU%f;VL%s;AC%s;MA%f;GO;" % (m, self.steps2mm,self.getCurrentSpeed(),self.getCurrentSpeed(),self.home * self.fs2mm))
                if self.getPropertyByLabel("Keep Log").getValue():
                    logname = os.path.join(self.getPropertyByLabel("path").getValue(),"positionLog.txt")
                    log = open(logname,"a")
                    log.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+" - %s: %f \n" % (m,self.home))
                    log.close()

            elif m=="AZ":
                self.ser.write("%s;UU%f;VL%s;AC%s;MA%f;GO;" % (m, self.steps2degrees,self.getCurrentSpeed(),self.getCurrentSpeed(),self.home * self.fs2mm))
                if self.getPropertyByLabel("Keep Log").getValue():
                    logname = os.path.join(self.getPropertyByLabel("path").getValue(),"positionLog.txt")
                    log = open(logname,"a")
                    log.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+" - %s: %f \n" % (m,self.home))
                    log.close()

        self.ready = True
        # read position and set value
        self.updatePosition()


    def disconnect(self):
        if self.ready:
            # move to home position
            for m in self.motors:
                if m=="AX" or m=="AY":
                    self.ser.write("%s;VL%s;AC%s;MA%f;GO;" % (m,self.getCurrentSpeed(),self.getCurrentSpeed(), self.home * self.fs2mm))
                    if self.getPropertyByLabel("Keep Log").getValue():
                        logname = os.path.join(self.getPropertyByLabel("path").getValue(),"positionLog.txt")
                        log = open(logname,"a")
                        log.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+" - %s: %f \n" % (m,self.home))
                        log.close()

                elif m=="AZ":
                    self.ser.write("%s;VL%s;AC%s;MA%f;GO;" % (m,self.getCurrentSpeed(),self.getCurrentSpeed(), self.home * self.fs2mm))
                    if self.getPropertyByLabel("Keep Log").getValue():
                        logname = os.path.join(self.getPropertyByLabel("path").getValue(),"positionLog.txt")
                        log = open(logname,"a")
                        log.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+" - %s: %f \n" % (m,self.home))
                        log.close()

            # wait for all motors to stop
            while(1):
                time.sleep(0.1)
                moving = False
                for m in self.motors:
                    if is_moving():
                        moving = True
                        break
                if not moving:
                    break
        self.ready = False

    def getCurrentMotor(self):
        id = self.getPropertyByLabel("axis").getValue()
        return self.motors[id]

    def getCurrentSpeed(self):
        id = self.getPropertyByLabel("speed").getValue()
        return self.speeds[id]


    def onStartStop(self, event):
        if self.getPropertyByLabel("movement").getValue() == "Start":
            pos = float(self.getPropertyByLabel("target").getValue())
            self.goto(pos)
        else:
            self.ser.write("%s;MA0;GO;" % (self.getCurrentMotor(), pos * self.fs2mm))   # stop all motors

    def updatePosition(self, event=None):
        # read position and set value
        self.getPropertyByLabel("position").setValue("%.f" % self.pos())

        # restart timer
        if self.is_moving():
            #update the postion one more time even if it's not moving
            self.getPropertyByLabel("position").setValue("%.f" % self.pos())
            self.updTimer = threading.Timer(0.3, self.updatePosition)
            self.updTimer.start()
        self.getPropertyByLabel("position").setValue("%.f" % self.pos())

    # return current position as a float
    def pos(self):
        pos0 = []
        self.ser.write("%s;RU;" % (self.getCurrentMotor()))
        posName= self.ser.read(self.readbytes).lower()
        for t in posName.split():
            try:
                pos0.append(float(t))
            except ValueError:
                pass
        #keep querying until it returns a number.
        while pos0==[]:
            self.ser.write("%s;RU;" % (self.getCurrentMotor()))
            posName= self.ser.read(self.readbytes).lower()
            for t in posName.split():
                try:
                    pos0.append(float(t))
                except ValueError:
                    pass
        return pos0[0]/ self.fs2mm

    # return current velocity as a float
    def vel(self):
        vel0 = []
        self.ser.write("%s;RV;" % (self.getCurrentMotor()))
        velName= self.ser.read(self.readbytes).lower()
        for t in velName.split():
            try:
                vel0.append(float(t))
            except ValueError:
                pass
        #keep querying until it returns a number.
        while vel0==[]:
            self.ser.write("%s;RV;" % (self.getCurrentMotor()))
            velName= self.ser.read(self.readbytes).lower()
            for t in velName.split():
                try:
                    vel0.append(float(t))
                except ValueError:
                    pass
        return vel0[0]/ self.fs2mm

    def goto(self, pos):
        print "axis %s moved from %s fs to %.0f fs at speed ~%s mm/s"%(self.getCurrentMotor(),self.getPropertyByLabel("position").getValue(),pos, self.getCurrentSpeed())
        if not self.ready:
            print "not ready"
            return
        # move to new position
        if self.getCurrentMotor() in ("AX" , "AY"):
            self.ser.write("%s;VL%s;AC%s;MA%f;GO;" % (self.getCurrentMotor(),self.getCurrentSpeed(),self.getCurrentSpeed(), pos * self.fs2mm))
        elif self.getCurrentMotor() =="AZ":
            self.ser.write("%s;VL%s;AC%s;MA%f;GO;" % (self.getCurrentMotor(),self.getCurrentSpeed(),self.getCurrentSpeed(), pos * self.fs2mm))
        if self.getPropertyByLabel("Keep Log").getValue():
            logname = os.path.join(self.getPropertyByLabel("path").getValue(),"positionLog.txt")
            log = open(logname,"a")
            log.write(strftime("%Y-%m-%d %H:%M:%S", gmtime())+" - %s: %f fs \n" % (self.getCurrentMotor(),pos))
            log.close()  
        time.sleep(0.2)
        # start update timer
        self.updTimer = threading.Timer(0.3, self.updatePosition)
        self.updTimer.start()


    # should return True if stage is still moving
    def is_moving(self):
        if not self.ready:
            return False
        vel0=self.vel()
        time.sleep(0.2)
        return (vel0!=0.0)

    def onMove(self, event):
        pos = float(self.getPropertyByLabel("position").getValue())
        self.goto(pos)