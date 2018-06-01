"""
.. module: FSRSModule
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

FSRSModule represents the base class for all modules in pyFSRS.
In addition to the class, this module provides some functions for dynamically
loading and handling FSRSModules.

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
import imp
import os
import threading
import FilePickerCtrl


# ##########################################################################################################################
# dynamically load the module given by filepath and
# returns a list with an instance of the class having the same name as the module
# if the module has a howMany() function, return as many instances as returned by howMany()
def load_from_file(filepath):
    """Dynamically load a FSRSModule given by `filepath` and try to return an instance of
    the module class. The module class has to have the identical name as the file!

    If the module provides a `howMany` function, this function initiates the necessary number of
    class instances and returns them as a list.

    .. note:: This function is not limited to FSRSModules but can be used to dynamically import any python module.

    :param str filepath: Filename of the module to load including the file extension (.pyc or .py).
    :returns: List of module class instances or None if no class could be found.
    """
    class_inst = None

    if not os.path.isfile(filepath):
        raise ValueError("Module does not exist!")

    mod_name, file_ext = os.path.splitext(os.path.split(filepath)[-1])

    if file_ext.lower() == '.pyc':
        py_mod = imp.load_compiled(mod_name, filepath)
    elif file_ext.lower() == '.py':
        py_mod = imp.load_source(mod_name, filepath)

    # check whether the module has a howMany function and if so, get the number of class instances that should be initiated
    if hasattr(py_mod, mod_name):
        inst = []
        N = 1
        if hasattr(py_mod, "howMany"):
            N = getattr(py_mod, "howMany")()
        for i in range(N):
            class_inst = getattr(py_mod, mod_name)()
            inst.append(class_inst)
        return inst
    return None


# ##########################################################################################################################
# text control validators
class NumValidator(wx.Validator):
    """Custom text control validator to be used internally with text inputs for numerical values.
    The validator test for conversion of the entered string into the desired numerical or string data type. If it fails,
    it displays a messge box asking the user to correct his input.

    :param str type: Type of allowed input ('float' = default, 'int', 'str').
    """
    def __init__(self, type='float'):
        wx.Validator.__init__(self)
        # self.Bind(wx.EVT_CHAR, self.OnChar)
        # self.Bind(wx.EVT_CHAR, self.OnText)
        self.oldtext = "0"
        self.type = type

    def Clone(self):
        return NumValidator(self.type)

    def Validate(self, win):
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()

        if self.type == 'float':
            try:
                float(text)
                return True
            except:
                wx.MessageBox("Please correct input! Only floating point values allowed!", "Invalid Input", wx.OK | wx.ICON_ERROR)
                return False
        elif self.type == 'int':
            try:
                int(text)
                return True
            except:
                wx.MessageBox("Please correct input! Only integer values allowed!", "Invalid Input", wx.OK | wx.ICON_ERROR)
                return False
        else:
            return True

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

    # def OnText(self, event):
    #     textCtrl = self.GetWindow()
    #     text = textCtrl.GetValue()
    #
    #     try:
    #         if self.type == "float":
    #             float(text)
    #         else:
    #             int(text)
    #     except:
    #         textCtrl.SetValue(self.oldtext)
    #         return
    #
    #     self.oldtext = text
    #     event.Skip()
    #
    # def OnChar(self, event):
    #
    #     textCtrl = self.GetWindow()
    #     text = textCtrl.GetValue()
    #
    #     keycode = int(event.GetUnicodeKey())
    #
    #     if keycode == wx.WXK_TAB:
    #         event.Skip()
    #         return
    #
    #     if keycode != wx.WXK_NONE:
    #         key = chr(keycode)
    #
    #         if self.type == "float":
    #             if key == "e":
    #                 if text.count("e") > 0:
    #                     return
    #             elif key == ".":
    #                 if text.count(".") > 0:
    #                     return
    #             elif key == "-":
    #                 if text.count("-") > 1:
    #                     return
    #             elif key not in string.digits:
    #                 return
    #         else:
    #             if key == "-":
    #                 if text.count("-") > 0:
    #                     return
    #             elif key not in string.digits:
    #                 return
    #
    #     event.Skip()


# ##########################################################################################################################
# base class for a property element associated to module
class ModProp():
    """Base class for a property element associated with a FSRSModule.

    A property has a name, a type, some value, a window handle to its control widget, an event handler and additional infos.
    Currently supported types are `label`, `input`, `choice`, `button`, `checkbox`, `progress`, `file`, `toggle`, and `spin`.
    Additional infos are:

        - *file*: `info` = 'open' / 'save' / 'path'
        - *toggle*: `info` = label of control element to be displayed next to the checkbox.
        - *spin*: `info` = (min, max)-tuple for spin control limits
        - *input*: `info` = allowed data type 'float' / 'int' / 'str' (or empty)
    """
    def __init__(self):
        self.label = ""
        self.labelwnd = None
        self.type = "label"
        self.value = ""
        self.choices = []
        self.handle = None
        self.event = None
        self.info = ""        # additional info used for some widgets:
        # 'file' -> 'info' = ['open', 'save', 'path']
        # 'toggle', 'checkbox' -> 'info' = label of control element, if empty, property label is used instead
        # 'spin' -> 'info' = (min, max) tuple for spin control limits
        # 'input' -> data type used for validation of input; "float" or "int"; if given, the EVT_TEXT event is connected to a validator

    def getInfo(self):
        """Return info field.
        """
        return self.info

    def getLabel(self):
        """Return label.
        """
        return self.label

    def getType(self):
        """Return type.
        """
        return self.type

    def getValue(self):
        """Returns the current property value. If a window handle exists, the property value is directly
        read out from that widget.
        """
        # if a handle exists, update the variable before returning it
        if self.handle is not None:
            if self.type in ["label", "button"]:
                self.value = self.handle.GetLabel()
            elif self.type == "choice":
                self.value = self.handle.GetSelection()
            elif self.type in ["input", "checkbox", "toggle", "progress", "file", "spin"]:
                self.value = self.handle.GetValue()

        return self.value

    def getChoices(self):
        """Returns choices.
        """
        return self.choices

    def getHandle(self):
        """Returns handle to widget, i.e., the wx control element.
        """
        return self.handle

    def getEvent(self):
        """Returns the event handler function.
        """
        return self.event

    def setLabelWnd(self, wnd):
        self.labelwnd = wnd

    def setLabel(self, txt):
        """Set label of property. Also updates labelwnd.
        """
        self.label = txt
        if self.labelwnd is not None:
            self.labelwnd.SetLabel(txt)

    def setType(self, val):
        """Set property type.

        Allowed values are 'label', 'input', 'choice', 'button', 'checkbox', 'toggle', 'file', 'progress', and 'spin'.
        """
        if val not in ['label', 'input', 'choice', 'button', 'checkbox', 'toggle', 'file', 'progress', 'spin']:
            raise ValueError("Not a valid property type!")
        self.type = val

    def setValue(self, val):
        """Set property value.

        Performs a rough sanity check depending on the type of property. If a widget is attached,
        also the value displayed in the widget is updated.
        """
        if(self.type in ['checkbox', 'toggle'] and ((val != 0 and val != 1) or (not val and val))):
            raise ValueError("Invalid value for property type checkbox: " + str(val))
        if(self.type == 'choice' and val != 0 and (val < 0 or val >= len(self.choices))):
            raise ValueError("Invalid value for property type choice! Index out of range (0..%d): %d" % (len(self.choices), val))
        if(self.type == 'progress' and (val < 0 or val > 100)):
            raise ValueError("Invalid value for property type progress (0..100): " + str(val))
        if(self.type == 'spin'):
            try:
                val = int(val)
            except:
                raise ValueError("Invalid value for property type spin: must be integer!:" + str(val))
        self.value = val

        if self.handle is not None:
            if self.type in ["label", "button"]:
                self.handle.SetLabel(str(val))
            elif self.type == "choice":
                self.handle.SetSelection(int(val))
            elif self.type in ["input", "file"]:
                self.handle.SetValue(str(val))
            elif self.type in ["checkbox", "toggle", "progress", "spin"]:
                self.handle.SetValue(val)

    def setChoices(self, ch=[]):
        """Set list of choices. Accepts a python list as argument.
        If a widget is attached to the property, the list of choices of the wxChoice box is
        also updated.
        """
        if not isinstance(ch, type([])):
            raise ValueError("New choices have to be passed as python list.")
        self.choices = ch

        if self.handle is not None and self.type == "choice":
            self.handle.Clear()
            try:
                self.handle.Append(self.choices)
            except:
                for s in self.choices:
                    self.handle.Append(s)
            self.handle.SetSelection(0)

        self.value = 0

    def setHandle(self, hndl):
        """Set window handle. `hndl` has to be a valid wxWidget.
        """
        self.handle = hndl

    def setEvent(self, evt=None):
        """Set event handler. `evt` is either a python function or None to disable the event handler.
        """
        self.event = evt

    def setInfo(self, info=""):
        """Set the info field according to the type of property.
        For some types ('file' and 'input'), this variable defines the appearance of the widgets and therefore has to be
        changed before the window handle is created.
        """
        if self.type == "file":
            if info not in ["open", "save", "path"]:
                raise ValueError("Info property has to be one of ['open', 'save', 'path'] for type 'file'.")
            if self.handle is not None:
                raise ValueError("Info property for type 'file' can only be changed before creation of handle!")
        if self.type == "input":
            if info not in ["float", "int", ""]:
                raise ValueError("Info property has to be one of ['float', 'int', ''] for type 'input'.")
            if self.handle is not None:
                raise ValueError("Info property for type 'input' can only be changed before creation of handle!")
        self.info = info

        if self.handle is not None:
            if self.type in ["checkbox", "toggle"]:
                self.handle.SetLabel(info)
            elif self.type == "spin":
                try:
                    self.handle.SetMin(int(self.info[0]))
                    self.handle.SetMax(int(self.info[1]))
                except:
                    pass

    # create the wx widget corresponding to the property type
    # parent is the wx.TreeCtrl instance that holds the widgets
    def createHandle(self, parent):
        """Create and return the wxWidget corresponding to the property type and attach to parent. `parent` is the wxTreeCtrl instance
        that holds the widgets. If an event handler is given, the correct binding is also created.
        """
        if self.type == 'label':
            wnd = wx.StaticText(parent, -1, self.value)

        elif self.type == 'input':
            wnd = wx.TextCtrl(parent, -1, value=self.value, validator=NumValidator(self.info), style=wx.TE_PROCESS_ENTER | wx.TE_RIGHT)
            if self.event is not None:
                wnd.Bind(wx.EVT_TEXT_ENTER, self.event)
                wnd.Bind(wx.EVT_KILL_FOCUS, self.event)

        elif self.type == 'choice':
            wnd = wx.Choice(parent, -1, choices=self.choices)
            wnd.Select(self.value)
            if self.event is not None:
                wnd.Bind(wx.EVT_CHOICE, self.event)

        elif self.type == 'button':
            wnd = wx.Button(parent, -1, self.value)
            if self.event is not None:
                wnd.Bind(wx.EVT_BUTTON, self.event)

        elif self.type == 'checkbox':
            if self.info != "":
                lbl = self.info
            else:
                lbl = self.label
            wnd = wx.CheckBox(parent, -1, lbl)
            wnd.SetValue(self.value)
            if self.event is not None:
                wnd.Bind(wx.EVT_CHECKBOX, self.event)

        elif self.type == 'toggle':
            if self.info != "":
                lbl = self.info
            else:
                lbl = self.label
            wnd = wx.ToggleButton(parent, -1, lbl)
            wnd.SetValue(self.value)
            if self.event is not None:
                wnd.Bind(wx.EVT_TOGGLEBUTTON, self.event)

        elif self.type == 'progress':
            wnd = wx.Gauge(parent, -1)
            wnd.SetRange(100)
            wnd.SetValue(self.value)

        elif self.type == 'file':
            wnd = FilePickerCtrl.FilePickerCtrl(parent, -1, mode=self.info)
            wnd.SetValue(self.value)
            if self.event is not None:
                wnd.Bind(FilePickerCtrl.EVT_FILE_SELECT, self.event)

        elif self.type == "spin":
            try:
                minmax = (int(self.info[0]), int(self.info[1]))
            except:
                minmax = (0, 100)
            wnd = wx.SpinCtrl(parent, -1, min=minmax[0], max=minmax[1], initial=self.value)
            if self.event is not None:
                wnd.Bind(wx.EVT_SPINCTRL, self.event)

        wnd.SetSize((150, 20))
        self.handle = wnd

        return wnd

    # enable / disable handle
    def freezeUI(self, freeze=True):
        """Enable or disable the user interface, i.e., the associated wxWidget when freeze is False or True.
        """
        if self.handle is not None:
            self.handle.Enable(not freeze)


# ##########################################################################################################################
# base class for pyFSRS modules - all devices, experiments, and general settings objects have to be derived from this class
class FSRSModule():
    """Base class for pyFSRS modules - all devices, experiments, and general settings objects have to be derived from this class.

    .. note:: There are a number of specialized subclasses for input and output devices, stages, experimental controls, etc. which define the necessary interface functions and new modules should be derived from those instead.
    """
    # do class initialization here
    def __init__(self):
        self.name = ""               #: Name of the module as it appears in the treectrl.
        self.properties = []         #: List of property entries, each entry is one line in the treectrl.
        self.propindex = {}          #: Dictionary containing a mapping from label to index - created on the go.
        self.category = ""           #: Category of the module; used by the main app for sorting.
        self.type = "module"         #: Type of module ('input', 'output', 'axis', 'experiment').

    # --------------------------------------------------------------------------------------------------------------------
    # module properties

    def addProperty(self, prop):
        """Add a property to the module.

        :param ModProp prop: Instance of ModProp containing the property to be added.
        :returns: Id (= index) of added property.
        """
        if type(prop).__name__ != "ModProp":
            raise ValueError("Property must be an instance of 'ModProp'.")
        id = len(self.properties)
        self.properties.append(prop)
        return id

    def setProperty(self, id, prop):
        """Set / overwrite an existing property of the module.

        :param int id: (= index) of added property.
        :param ModProp prop: Instance of ModProp containing the new property.
        """
        if type(prop).__name__ != "ModProp":
            raise ValueError("Property must be an instance of 'ModProp'.")
        if id < 0 or id > len(self.properties):
            raise ValueError("Index out of range: " + str(id))
        self.properties[id] = prop

    def getProperty(self, id):
        """Returns the property with given id.
        """
        if id < 0 or id > len(self.properties):
            raise ValueError("Index out of range: " + str(id))
        return self.properties[id]

    def getPropertyByLabel(self, label):
        """Extremely useful function that returns the property whose label matches `label`.
        It is sufficient if the property label contains the string `label` irrespective of upper or lowercase lettering.
        """
        if label in self.propindex:
            return self.properties[self.propindex[label]]
        else:
            for i in range(len(self.properties)):
                if self.properties[i].getLabel().lower().find(label.lower()) != -1:
                    self.propindex[label] = i
                    return self.properties[i]
        raise ValueError("Property label not found: %s." % label)

    def hasProperty(self, label):
        """Returns true if a property width the given label exists.
        It is sufficient if the property label contains the string `label` irrespective of upper or lowercase lettering.
        """
        if label in self.propindex:
            return True
        else:
            for i in range(len(self.properties)):
                if self.properties[i].getLabel().lower().find(label.lower()) != -1:
                    self.propindex[label] = i
                    return True
        return False


    # convenience function to populate the list of properties at startup using a list of python dictionaries
    # required keys are 'label' and 'type'
    # if type is not label, additional keys are required: 'event' = string name of event handler function
    # if type == choice: 'choices'
    # the handle field is populated when the
    def parsePropertiesDict(self, dct):
        """Create a list of properties directly by parsing a list of python dictionaries defining those properties.

        :param list dct: Python list of dictionaries defining the properties.

        Required keys are:

            - *label*: Name of the property.
            - *type*: Type of the property (`label`, `input`, `choice`, `button`, `checkbox`, `progress`, `file`, `toggle`, and `spin`).
            - *value*: Initial value of the property according to its type.
            - *choices*: If type='choice', a list of choice strings has to be given.

        If type is 'file', 'toggle', 'spin', or 'input', also the *info*-key should to be present:

            - *file*: `info` = 'open' / 'save' / 'path'
            - *toggle*: `info` = label of control element to be displayed next to the checkbox.
            - *spin*: `info` = (min, max)-tuple for spin control limits
            - *input*: `info` = allowed data type 'float' / 'int' / 'str' (or empty)

        An event handler may be given by its function name within the same module and passed along with the *event*-key.

        Window handles are not parsed and will be populated automatically by `initialize`.
        """
        for d in dct:
            p = ModProp()

            if 'label' not in d:
                raise ValueError("Missing key 'label' in properties dict!")
            if 'type' not in d:
                raise ValueError("Missing key 'type' in properties dict!")
            if 'value' not in d:
                raise ValueError("Missing key 'value' in properties dict!")
            p.setType(d['type'])
            p.setLabel(d['label'])

            if d['type'] == 'choice':
                if 'choices' not in d:
                    raise ValueError("Missing key 'choices' in properties dict!")
                p.setChoices(d['choices'])

            if 'info' in d:
                p.setInfo(d['info'])

            p.setValue(d['value'])

            if 'event' in d and d['event'] is not None:
                p.setEvent(getattr(self, d['event']))    # create a callable method from string name

            self.properties.append(p)

    # --------------------------------------------------------------------------------------------------------------------
    # startup event handlers / functions
    # pass list of other modules in others to make module aware of its fellows
    # this version returns the number of instances that are in the list before this one
    def initialize(self, others=[]):
        """Startup handler called by the pyFSRS app after all modules have been loaded.

        .. important:: This function should be overwritten by any derived FSRSModule to perform the module specific initialization steps.

        :param list others: A list of all loaded and available FSRSModules. Use this to a) check how many instances of this module have been loaded already and b) make connections to available hardware, for instance.
        :returns: Number of modules of the same type that are already in the list.
        """
        # count how many instances are before this one
        count = 0
        for m in others:
            if m is self:
                break
            elif m.name == self.name:
                count += 1
        return count

    # --------------------------------------------------------------------------------------------------------------------
    # shutdown event handlers / functions

    # called when main application is about to quit; return False if there is something going on that prevents closing
    def canQuit(self):
        """This function is called by the pyFSRS app when the user requests to close the program.
        If this module is ok with leaving, return True, otherwise return False. For instance, when a scan is still running
        this would be the right time to ask whether the user really wants to quit.

        .. important:: This function should be overwritten by any derived FSRSModule to perform the module specific shutdown steps.
        """
        return True

    # this function is called when the application is shut down; do all the clean up here (close drivers, etc)
    def shutdown(self):
        """This function is called by the pyFSRS app when the program is about to close. At this point, no veto is possible.
        Use this function to perform the necessary steps for a safe exit, like close connections to libraries or moving any stages to
        their initial positions, and so on.

        .. important:: This function should be overwritten by any derived FSRSModule to perform the module specific shutdown steps.
        """
        pass

    # --------------------------------------------------------------------------------------------------------------------
    # enable / disable user interface
    def freezeUI(self, freeze=True):
        """Enable of disable the user interface, i.e. all property widgets when freeze is False or True.
        This function is handy to block the user from messing with parameters during a scan, for example.
        """
        for p in self.properties:
            p.freezeUI(freeze)


# ##########################################################################################################################
# base class for any input device
class Input(FSRSModule):
    """Base class for any input device that is used to read a single value. Examples include lock-in-amplifiers or DAQs.
    """
    def __init__(self):
        FSRSModule.__init__(self)
        self.type = "input"

    # this is the only additional function an input device has to have
    # returns some value
    def read(self):
        """Returns a single measurement value.

        .. important:: This function has to be overwritten by any derive input module to implement the device specific code.
        """
        return 0


# ##########################################################################################################################
# base class for any camera device
class Camera(FSRSModule):
    """Base class for any camera device that is used to read a 3xN array of data for FSRS and TA.
    The module type is 'input', so that it can be used in place of any input device.
    """
    def __init__(self):
        FSRSModule.__init__(self)
        self.type = "input"

    # this is the only additional function an input device has to have
    # returns some value
    def read(self):
        """Returns a single measurement value.

        .. important:: This function has to be overwritten by any derive input module to implement the device specific code.
        """
        return 0

    def readNframes(self, N, canQuit=None):
        """Returns a 3xN array of data with columns 'pumpOn / pumpOff', 'pumpOn', 'pumpOff'.

        .. important:: This function has to be overwritten by any derived camera module to implement the device specific code.

        :param int N: Number of frames to read.
        :param threading.Event() canQuit: Pass along the theading event that may be used to stop acquisition or None if this is not desired.
        :returns: 3xN array with measured data.
        """
        return [[0] * N, [0] * N, [0] * N]


# ##########################################################################################################################
# base class for any output device
class Output(FSRSModule):
    """Base class of a generic output module that is used to send a value to some device. Examples include DAQs or digital output channels.
    """
    def __init__(self):
        FSRSModule.__init__(self)
        self.type = "output"

    # this is the only additional function an output device has to have
    # write some value to the output
    def write(self, value):
        """Write 'value' to the device.

        .. important:: This function has to be overwritten by any derived output module to implement the device specific code.
        """
        pass


# ##########################################################################################################################
# base class for any axis / stage device
class Axis(FSRSModule):
    """Base class for any axis or stage device.
    """
    def __init__(self):
        FSRSModule.__init__(self)
        self.type = "axis"

    # return current position
    def pos(self):
        """Return current position.

        .. important:: This function has to be overwritten by any derived motor class to implement the device specific code.
        """
        return 0

    # goto new position
    def goto(self, pos):
        """Go to specified position.

        .. important:: This function has to be overwritten by any derived motor class to implement the device specific code.
        """
        pass

    # should return True if stage is still moving
    def is_moving(self):
        """Return True if stage is moving, otherwise False.

        .. important:: This function has to be overwritten by any derived motor class to implement the device specific code.
        """
        return False


# ##########################################################################################################################
# base class for any experiment
class Experiment(FSRSModule):
    """Base class for any experiment control module. These are actually the heart of pyFSRS and control all experimental
    conditions as well as all attached hardware.

    When creating the properties, you should create a start/stop button with the label "Start", which is used by the experiment control functions.
    """
    def __init__(self):
        FSRSModule.__init__(self)
        self.type = "experiment"

        self.others = []
        self.btnOldLabel = ""

        # when creating the properties, you should create a start/stop button with the label "Start"

        # for any experiment, the actual measurement is done in a new thread which communicates with the main GUI via call back functions
        self.scanThread = None
        self.running = False

    # ################################################################################
    # Initialize Experiment
    # use this function to get access to necessary devices
    # but also to enable / disable those user interfaces
    def initialize(self, others=[]):
        """Save list of other modules to get access to hardware but also to be able to enable / disable those user interfaces during a scan.

        .. important:: This function may be overwritten in your experiment class to implement some specific code but do not forget to store the list of other modules.
        """
        self.others = others

    # ################################################################################
    # Start / Stop the Thread
    def start(self, thread, **argv):
        """Start the measurement thread and deal with the button labels.

        :param threading.Thread thread: An instance of the measurement thread class, which is a subclass of threading.Thread.
        :param mixed argv: A list of parameters that are passed along to the measurement thread.
        """
        if self.scanThread is not None:
            return

        try:
            btn = self.getPropertyByLabel("start")
            self.btnOldLabel = btn.getHandle().GetLabel()
            btn.getHandle().SetLabel("STOP")
        except:
            pass

        self.scanThread = thread(self, **argv)
        self.scanThread.start()

    def stop(self):
        """Stop the measurement by sending the stop signal to the thread.
        """
        if self.scanThread is not None:
            self.scanThread.stop()

    # ################################################################################
    # 'Event' Handlers which are called by the Thread as Call Back functions
    def onStarted(self):
        """Event handler that gets called by the measurement thread once it has started the scan.
        Blocks the user interface but keeps the stop-button alive.
        """
        # block UI
        for m in self.others:
            m.freezeUI(True)

        # but keep the stop button active
        try:
            btn = self.getPropertyByLabel("start")
            btn.freezeUI(False)
        except:
            pass

        self.running = True

    def onUpdate(self, *args):
        """Event handler that gets called periodically by the measurement thread to send data or
        just status updates to the GUI.

        .. important:: This function has to be overwritten in your derived experiment class to implement your specific code.
        """
        pass

    def onFinished(self):
        """Event handler that gets called by the measurement thread once the scan has been finished.
        Waits for the thread to die, changes the start/stop-button label and reactivates the user interface.
        """
        # make sure the thread is done
        if self.scanThread is not None and self.scanThread.is_alive():
            self.scanThread.join()
            self.scanThread = None

        # try to change button text
        try:
            btn = self.getPropertyByLabel("start")
            btn.getHandle().SetLabel(self.btnOldLabel)
        except:
            pass

        # free UI
        for m in self.others:
            m.freezeUI(False)

        self.running = False

    # ################################################################################
    # shutdown functions for experiment module

    # take care about the running scan thread
    def canQuit(self):
        """Shutdown handler that checks for a running measurement thread. If there is a scan running, it prompts the user to confirm aborting the scan before closing.
        """
        if(self.scanThread is None):
            return True
        elif(self.scanThread.is_alive()):
            if wx.MessageBox("Scan is running! Really quit?", "Quit", style=wx.YES | wx.NO) == wx.YES:
                self.scanThread.stop()
                self.scanThread.join()
                return True
        else:
            return False

    # take care about the running scan thread
    def shutdown(self):
        """Shutdown handler that kills the measurement thread and waits for it to die.
        """
        if(self.scanThread is not None and self.scanThread.is_alive()):
            self.scanThread.stop()
            self.scanThread.join()


# ################################################################################
# helper class for experiment providing the actual scan thread
class ExperimentThread(threading.Thread):
    """Prototype for a measurement thread that may be used for the actual experiment. It is subclassed from
    `threading.Thread` and provides the same functionality. The thread is started by calling its `start`-function
    and stopped by calling its `stop`-function. The actual measurement routine is `run`, which has to be overwritten in
    your derived measurement thread.

    .. important:: Provide your own __init__ routine based on this one to handle the measurement parameters correctly.

    :param FSRSModule.FSRSModule parent: Parent module whose event handlers are called by this measurement thread.
    :param mixed argv: Additional arguments that are passed to the thread. These are essentially the parameters that control the experiment, like start and stop positions for the stage and number of frames to capture and so on.
    """
    def __init__(self, parent, **argv):
        threading.Thread.__init__(self)
        self.parent = parent
        self.canQuit = threading.Event()    #: User stop event, handles also sleep-functionality.
        self.canQuit.clear()

    # the main GUI calls this function to terminate the thread
    def stop(self):
        """Stop the thread by setting the threading.Event `canQuit` to True.
        """
        self.canQuit.set()

    # this is the actual scan routine
    def run(self):
        """This is the actual scan routine.

        .. important:: This function has to be overwritten by your implementation to handle your specific code.

        A rough prototype should look like this::

            def run(self):
                # send started-event to GUI
                wx.CallAfter(self.parent.onStarted)

                # enter main loop - iterate until canQuit is True
                while(self.canQuit.isSet() == 0):

                    # put here your actual measurement protocol
                    # stage move to here and there
                    # wait for stage
                    # read data

                    # do not forget to send data or status information periodically to GUI
                    wx.CallAfter(self.parent.onUpdate, *args)

                # send terminated-event to GUI
                wx.CallAfter(self.parent.onFinished)

        """
        # send started-Event
        wx.CallAfter(self.parent.onStarted)

        # enter main loop
        while(self.canQuit.isSet() == 0):
            pass

            # send data to main GUI
            # wx.CallAfter(self.parent.onUpdate, *args)

        # send terminated-Event
        wx.CallAfter(self.parent.onFinished)
