"""
.. module: FilePickerCtrl
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

A simple file and path picker widget consisting of a text field and a button.

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
import wx.lib.newevent
import os

FileSelectEvent, EVT_FILE_SELECT = wx.lib.newevent.NewEvent()


class FilePickerCtrl(wx.Panel):
    """FilePickerCtrl is a simple file picker widget for wxPython consisting of a text-field and a
    'select file'-button.

    :param wxWindow parent: Parent window.
    :param int id: Widget it (default=-1).
    :param str startDir: Initial directory to display in search dialog (default='' for current).
    :param str mode: Type of dialog ('open', 'save', 'path' = default).
    :param kwargs: Other parameters that are passed on to the wxPanel constructor.
    """
    def __init__(self, parent, id=-1, startDir='', mode='path', **kwargs):
        wx.Panel.__init__(self, parent, id, **kwargs)

        self.startDir = startDir

        if mode not in ["open", "save", "path"]:
            raise ValueError("Mode must be 'path', 'open' or 'save'!")
        if mode == "open":
            self.mode = wx.FD_OPEN
            self.dlgt = "Choose file to open.."
        elif mode == "save":
            self.mode = wx.SAVE
            self.dlgt = "Choose file to save.."
        else:
            self.mode = None
            self.dlgt = "Choose path.."

        # create widget
        self.rborder = 0

        self.outersizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.input = wx.TextCtrl(self, -1, "")
        self.button = wx.Button(self, -1, "...", style=wx.BU_EXACTFIT)
        self.sizer.Add(self.input, 1, wx.EXPAND | wx.RIGHT, 3)
        self.sizer.Add(self.button, 0)
        self.outersizer.Add(self.sizer, 1, wx.EXPAND | wx.RIGHT, self.rborder)

        self.SetSizer(self.outersizer)
        self.Fit()
        self.SetAutoLayout(True)

        if 'size' in kwargs:
            self.SetSize(kwargs['size'])

        self.button.Bind(wx.EVT_BUTTON, self.onBrowse)


    def GetSize(self):
        """Return wxSize-object containing widget dimensions.
        """
        size = wx.Panel.GetSize(self)
        return wx.Size(size[0] - self.rborder, size[1])


    def SetSize(self, w, h=None):
        """Set widget size.

        :param mixed w: Width in pixel if h is not None. Otherwise tuple containing width and height.
        :param int h: Height in pixel (default=None).
        """
        if h is None:
            wx.Panel.SetSize(self, (w[0] + self.rborder, w[1]))
        else:
            wx.Panel.SetSize(self, (w + self.rborder, h))


    def GetValue(self):
        """Return selected path.
        """
        return self.input.GetValue()


    def SetValue(self, value):
        """Set current path.
        """
        self.input.SetValue(str(value))


    def Enable(self, value=True):
        """Enable or disable widget when value is True (default) or False.
        """
        self.input.Enable(value)
        return self.button.Enable(value)


    def Disable(self):
        """Disable widget.
        """
        self.Enable(False)


    def onBrowse(self, event):
        """Handle the button click event by displaying a file or path dialog.

        Emits a `FileSelectEvent` when the user clicks OK.
        """
        current = self.GetValue()
        directory = os.path.split(current)

        if os.path.isdir(current):
            directory = current
            current = ''
        elif directory and os.path.isdir(directory[0]):
            current = directory[1]
            directory = directory[0]
        else:
            directory = self.startDir

        if self.mode is None:
            dlg = wx.DirDialog(self, self.dlgt, directory, wx.DD_DIR_MUST_EXIST)
        else:
            dlg = wx.FileDialog(self, self.dlgt, directory, current, "*.*", self.mode)

        if dlg.ShowModal() == wx.ID_OK:
            self.SetValue(dlg.GetPath())

            # Create the event
            evt = FileSelectEvent(filename=self.GetValue())

            # Post the event
            wx.PostEvent(self, evt)

        dlg.Destroy()
