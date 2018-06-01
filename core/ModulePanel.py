"""
.. module: ModulePanel
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

A ModulePage is a container widget that holds a variable number of ModulePanels.
A ModulePanel is a customized collapsible wxPanel for displaying a list of labeled wxWidgets.
While these two are mainly used for showing pyFSRS modules and their properties, the widgets
can be used very general.

Example usage::

    import wx
    from ModulePanel import *

    # create wxPython app
    app = wx.App()
    frame = wx.Frame(None, title="pyFSRS - Test module panel")
    frame.SetBackgroundColour(wx.Colour(255, 255, 255))

    # create a new ModulePage
    page = ModulePage(frame, -1)

    # create ModulePanels and add them to ModulePage
    pane1 = ModulePanel(page, -1, label="Module 1")
    pane1.Add("some", "text")
    pane1.Add("Left", wx.TextCtrl(pane1.GetPane(), -1, "Hallo Welt"))
    page.AddPanel(pane1)

    pane2 = ModulePanel(page, -1, color=wx.Colour(0, 0, 255), label="Module 2")
    pane2.Add("some", "text")
    pane2.Add("Left", wx.TextCtrl(pane2.GetPane(), -1, "Hallo Welt"))
    page.AddPanel(pane2)

    # this demonstrates how widgets can be added after creating the panel
    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 3"))).Add("A", "Line")
    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 4"))).Add("B", "Line")
    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 5"))).Add("C", "Line")
    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 6"))).Add("D", "Line")

    # show the fram and run the app
    frame.Show()
    app.MainLoop()


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
import itertools

PanelHideEvent, EVT_PANEL_HIDE = wx.lib.newevent.NewEvent()  #: event that is generated when one of the panels is resized


# panel main class
class ModulePanel(wx.Panel):
    """A collapsible wxPanel that is used to display FSRSModules and their properties.
    This panel arranges child widgets row by row with a label printed in the left column and the actual widget displayed in the right column.

    Accepts wxPanel's standard parameters. Especially

        - *color*: wxColour that defines the color of the panel's frame. This value indirectly defines also the color of the title font. If it is a light color, the title is black, otherwise it is white.
        - *bgcolor*: wxColour that defines the background color of the panel's interior.
        - *label*: Title of the panel that appears on the top.
        - *font*: wxFont for the panel's title and its children.
    """
    def __init__(self, *args, **kwargs):

        clr = kwargs.pop("color", wx.Colour(255, 0, 0))
        bgclr = kwargs.pop("bgcolor", wx.Colour(255, 255, 255))
        fnt = kwargs.pop("font", wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False))
        lbl = kwargs.pop("label", "ModulePanel")

        wx.Panel.__init__(self, *args, **kwargs)

        self.SetLabel(lbl)
        self.SetForegroundColour(clr)
        self.SetBackgroundColour(bgclr)
        self.SetFont(fnt)

        # expanded or not?
        self.expanded = True        #: Expanded or not.

        self.dfltCursor = self.GetCursor()

        # construct a set of spacers to achieve the correct spacing to the sides
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        midsizer = wx.BoxSizer(wx.VERTICAL)

        # this panel is put in between to enable hiding of the contents
        self.mainpanel = wx.Panel(self, -1)

        # this is the central sizer, which layouts the widgets in two columns
        self.centralsizer = wx.FlexGridSizer(cols=2, hgap=10, vgap=10)
        self.centralsizer.AddGrowableCol(1, 1)

        # stack together
        self.mainpanel.SetSizer(self.centralsizer)
        midsizer.Add(self.mainpanel, 1, wx.EXPAND | wx.ALL, 10)
        mainsizer.Add(midsizer, 1, wx.EXPAND | wx.TOP, 20)
        self.SetSizer(mainsizer)

        # event bindings
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.onEraseBackground)
        self.Bind(wx.EVT_SIZE, self.onResize)
        self.Bind(wx.EVT_LEFT_DOWN, self.onLMouseDown)
        self.Bind(wx.EVT_MOTION, self.onMouseMove)

    # EVENTS
    def mouseInBtn(self):
        """Returns True if mouse hovers above the panel's title bar, which is used to collapse or uncollapse the panel.
        """
        # get mouse position in window
        x, y = self.ScreenToClient(wx.GetMousePosition()).Get()
        if y >= 0 and y <= 20:
            return True
        else:
            return False

    def onMouseMove(self, event):
        """Mouse move event handler that controls cursor appearance.
        """
        if self.mouseInBtn():
            self.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        else:
            self.SetCursor(self.dfltCursor)

        event.Skip()

    def onLMouseDown(self, event):
        """Mouse left-click event handler that controls collapsing or uncollapsing the panel."
        """
        if self.mouseInBtn():
            self.Hide(self.expanded)
        event.Skip()

    def onEraseBackground(self, event):
        """This event is used to paint the panel's frame in the background.
        """
        # get paint dc
        dc = event.GetDC()

        # clear window
        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

        dcwidth, dcheight = self.GetClientSize()
        if not dcwidth or not dcheight:
            return

        # draw container
        clr = self.GetForegroundColour()
        dc.SetBrush(wx.Brush(clr))
        dc.SetPen(wx.Pen(clr, width=2))
        dc.DrawRoundedRectangle(0, 0, dcwidth, 20, 10)
        dc.DrawRectangle(0, 10, dcwidth, 10)
        if self.expanded:
            dc.DrawLine(1, 10, 1, dcheight)
            dc.DrawLine(dcwidth - 1, 10, dcwidth - 1, dcheight)
            dc.DrawLine(0, dcheight - 1, dcwidth - 1, dcheight - 1)

        # write label and open/close button
        r, g, b = clr.Red(), clr.Green(), clr.Blue()
        if r + g + b > 380:
            fclr = wx.Colour(0, 0, 0)
        else:
            fclr = wx.Colour(255, 255, 255)
        dc.SetPen(wx.Pen(fclr, width=1))
        dc.SetBrush(wx.Brush(clr))
        dc.SetFont(self.GetFont().Bold())
        dc.SetTextForeground(fclr)
        dc.SetTextBackground(clr)

        dc.DrawRectangle(5, 5, 11, 11)
        dc.DrawLine(7, 10, 14, 10)
        if not self.expanded:
            dc.DrawLine(10, 7, 10, 14)
        lbl = self.GetLabel()
        txtW, txtH = dc.GetTextExtent(lbl)
        dc.DrawText(lbl, 30, 10 - txtH / 2)

    def onResize(self, event):
        """Handle a resize by repainting the panel.
        """
        self.Refresh()
        event.Skip()

    # MEMBER / LAYOUT FUNCTIONS
    # returns the main panel which is the panel that serves as parent for the child widgets
    def GetPanel(self):
        """Returns the main panel, which serves as parent to the child widgets.
        """
        return self.mainpanel

    # add a widget to the panel
    # label is displayed in the left column
    # if wnd is a string, create a static text widget
    def Add(self, label, wnd):
        """Add a widget to the panel.

        :param str label: Text / label to be displayed in the left column.
        :param mixed wnd: Either wxWidget to be added in the right column or a string to be added as simple static text.
        """
        label = wx.StaticText(self.mainpanel, -1, label)
        self.centralsizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        if isinstance(wnd, basestring):
            self.centralsizer.Add(wx.StaticText(self.mainpanel, -1, wnd), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
        else:
            self.centralsizer.Add(wnd, 1, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

        pnsize = self.mainpanel.GetSize()
        self.SetMinSize((-1, pnsize[1] + 20))

        return label

    # EXPAND / HIDE FUNCTIONS

    # call this function only after the main frame has been shown!
    def Hide(self, hide=True):
        """(Un-) Hide the panel's content and (expand) shrink it to show its (full content) title bar when hide is (False) True.
        Call this function only after the main frame has been initialized.
        Emits a `PanelHideEvent` to notify other panels of its action.
        """
        self.expanded = not hide
        self.mainpanel.Show(not hide)

        if hide:
            self.SetMaxSize((-1, 20))
        else:
            self.SetMaxSize((-1, 100000))

            # Create the event
            evt = PanelHideEvent(panel=self)

            # Post the event
            wx.PostEvent(self, evt)

        self.GetParent().Layout()


class ModulePage(wx.Panel):
    """Container widget holding a number of ModulePanels. Only one panel may be expanded at a time.
    """
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.panels = []
        self.SetSizer(self.sizer)
        self.colors = itertools.cycle([wx.Colour(255, 0, 0), wx.Colour(255, 150, 0), wx.Colour(255, 255, 0), wx.Colour(0, 255, 0), wx.Colour(128, 128, 255), wx.Colour(0, 0, 255)])

    def AddPanel(self, panel):
        """Add a ModulePanel.

        :params ModulePanel panel: Panel which to add to the ModulePage.
        :returns: Id of added panel.
        """
        id = self.GetNumPanels()

        if len(self.panels) > 0:
            panel.Hide(True)

        panel.SetForegroundColour(next(self.colors))

        panel.Bind(EVT_PANEL_HIDE, self.onPanelHide)
        self.panels.append(panel)
        self.sizer.Add(panel, 1, wx.EXPAND | wx.ALL, 1)
        self.Layout()

        return id

    def GetNumPanels(self):
        """Returns number of panels on this page.
        """
        return len(self.panels)

    def GetPanel(self, id):
        """Returns the ModulePanel with given id.

        :param int id: Id or index of panel to return.
        :returns: Instance of ModulePanel.
        """
        if id < 0 or id >= len(self.panels):
            raise ValueError("ID is out of range!")
        return self.panels[id]

    def onPanelHide(self, event):
        """Event handler to manage the exclusive expansion of a single panel at a time by closing all other panels.
        """
        for p in self.panels:
            if p is not event.panel:
                p.Hide(True)


if __name__ == '__main__':
    app = wx.App()
    frame = wx.Frame(None, title="pyFSRS - Test module panel")
    frame.SetBackgroundColour(wx.Colour(255, 255, 255))

    page = ModulePage(frame, -1)

    pane1 = ModulePanel(page, -1, label="Module 1")
    pane1.Add("some", "text")
    pane1.Add("Left", wx.TextCtrl(pane1.GetPane(), -1, "Hallo Welt"))

    page.AddPanel(pane1)

    pane2 = ModulePanel(page, -1, color=wx.Colour(0, 0, 255), label="Module 2")
    pane2.Add("some", "text")
    pane2.Add("Left", wx.TextCtrl(pane2.GetPane(), -1, "Hallo Welt"))

    page.AddPanel(pane2)

    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 3"))).Add("A", "Line")
    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 4"))).Add("B", "Line")
    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 5"))).Add("C", "Line")
    page.GetPanel(page.AddPanel(ModulePanel(page, -1, label="Module 6"))).Add("D", "Line")
    frame.Show()

    app.MainLoop()
