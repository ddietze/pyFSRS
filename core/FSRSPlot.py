"""
.. module: FSRSPlot
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

FSRSPlot is a lightweight plotting widget for wxPython for displaying pyFSRS measurement results.
It supports multiple line and scatter plots, contour plots and image plots.
While contour plots work on non-equidistantly sampled data and produce nice interpolated plots,
image plots operate on 2d arrays and provide an enourmous advantage in speed.

Further features include lin / log scale for x, y, and z axes (individually) as well as
reading data coordinates with mouse cursor, two independent data cursors for exploring line/scatter
data values and displaying the difference value.

Example usage::

    import wx
    import numpy as np
    from FSRSPlot import *

    # setup a wxPython app
    app = wx.App()

    # get an instance of a plot frame
    frame = PlotFrame(None, title="pyFSRS - Test plot panel", size=(640, 480))
    frame.plotCanvas.setColormap("blue")

    # get some nice data
    x = np.linspace(-10, 10, 64)
    y = np.linspace(-10, 10, 64)

    X, Y = np.meshgrid(x, y)
    z = np.exp(-(X**2 +Y**2) / 5.0**2) * np.sin(X)
    frame.plotCanvas.addImage(x, y, z)
    frame.plotCanvas.addLine(x, -5 + 10.0 * np.exp(-x**2 / 5.0**2))

    # show frame and start app
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
import numpy as np
import itertools


# plot panel main class
class FSRSPlot(wx.Panel):
    """The FSRSPlot class is derived from wxPanel and provides a lightweight plotting interface
    for wxPython that not only supports line/scatter plots but also image and contour plots.

    I have kept the number of functions to control the layout to a minimum. Rather, the user is
    encouraged to directly mess with the class member variables. A list of variables and their default values are given in the following::

        # display the cross cursor when mouse is present in plot area
        self.showCross = True

        # display a grid
        self.showGrid = True

        # linewidth, markerstyle and colors for scatter / line plot
        self.markersize = 2
        self.linewidth = 2

        # background color
        self.bgcolor = wx.Colour(255, 255, 255)

        # margin of plotting area to boundary of panel in pixels
        self.leftmargin = 60
        self.bottommargin = 30

        # axis and ticks; font and colors
        self.ticklength = 5
        self.axisPen = wx.Pen(wx.Colour(0, 0, 0), width=2, style=wx.PENSTYLE_SOLID)
        self.font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        # display Delta-value, i.e. difference between cursors A and B
        self.deltafont = wx.Font(20, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.deltafontPen = wx.Pen(wx.Colour(30, 0, 250), width=1, style=wx.PENSTYLE_SOLID)

        # grid
        self.gridPen = wx.Pen(wx.Colour(128, 128, 128), width=1, style=wx.PENSTYLE_DOT)

        # mouse crosshair
        self.crossPenDark = wx.Pen(wx.Colour(0, 0, 0), width=1, style=wx.PENSTYLE_SOLID)
        self.crossPenLight = wx.Pen(wx.Colour(255, 255, 255), width=1, style=wx.PENSTYLE_SOLID)

        # list of line colors; the color is cycled through the array for each new line or point
        self.linescolor = [wx.Colour(255, 0, 0), wx.Colour(255, 128, 128), wx.Colour(0, 0, 255),
                           wx.Colour(128, 128, 255) , wx.Colour(0, 255, 0), wx.Colour(128, 255, 128)]

    """
    def __init__(self, parent, id=-1, *args, **kwargs):
        wx.Panel.__init__(self, parent, id, *args, **kwargs)
        self.SetWindowStyle(self.GetWindowStyle() | wx.WANTS_CHARS)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        # setup widget
        self.initVariables()

        # Bind the events related to our control: first of all, we use a
        # combination of wx.BufferedPaintDC and an empty handler for
        # wx.EVT_ERASE_BACKGROUND (see later) to reduce flicker
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnResize)

        # mouse events
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLMouseDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRMouseDown)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)

        # keyboard events
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def initVariables(self):
        """Init internally used variables and parameters.
        """
        # data
        # data contains a list of plot elements where
        # data = [ [[x1, y1], [x2, y2], ...[xN, yN]], [..] ] for line/scatter,
        # data = [ [[x1, x2, ...xN], [y1, y2, ..., yM], [[z11, z12, ...z1N], [z21, ..], ..]] ] for contour and
        # data = [ [[x0, xN], [y0, yN], index] ] for image; x0, xN are min/max values
        # and type one of "line", "scatter", "contour", and "image"
        self.data = []               # plot data
        self.data_types = []         # type of data stored in self.data
        self.data_extent = []        # list of data ranges [xmin, xmax, ymin, ymax]
        self.images = []             # list of wx.Bitmap objects

        # -------------------------
        # internally used variables

        # memory dc for storing contour plots, which are time intensive to replot
        self.contourDC = wx.MemoryDC()            # this stores the created image
        self.contourDCValid = False                # False -> redraw the contour plot, True -> copy from memoryDC

        # data min/max and ticks for axis
        self.plotXMin = 0
        self.plotXMax = 1
        self.plotYMin = 0
        self.plotYMax = 1
        self.plotZMin = 0
        self.plotZMax = 1
        self.XTicks = []
        self.YTicks = []
        self.lblx = []
        self.lbly = []

        # mapping from data to screen
        self.map_ax = 1
        self.map_bx = 0
        self.map_ay = 1
        self.map_by = 0

        # size of actual plot area
        self.dcleft = 0
        self.dctop = 0
        self.dcright = 0
        self.dcbottom = 0

        # mouse control variables
        self.mousePos = wx.Point()
        self.mouseIn = False
        self.mouseX1 = None            # cursor positions in data coordinates!
        self.mouseX2 = None
        self.mouseN = 0                # index of line the cursors are assigned to
        self.cursor1 = [0, 0]        # data value at cursor position
        self.cursor2 = [0, 0]

        # -------------------------
        # layout parameters

        # display the cross cursor when mouse is present in plot area
        self.showCross = True

        # display a grid
        self.showGrid = True

        # background color
        self.bgcolor = wx.Colour(255, 255, 255)

        # margin of plotting area to boundary of panel in pixels
        self.leftmargin = 60
        self.bottommargin = 30

        # axis and ticks; font and colors
        self.ticklength = 5
        self.axiswidth = 2
        self.font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.axiscolor = wx.Colour(0, 0, 0)
        self.gridcolor = wx.Colour(128, 128, 128)

        self.deltafont = wx.Font(20, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.deltafontcolor = wx.Colour(30, 0, 250)

        # set pen
        self.axisPen = wx.Pen(self.axiscolor, width=self.axiswidth, style=wx.PENSTYLE_SOLID)
        self.gridPen = wx.Pen(self.gridcolor, width=1, style=wx.PENSTYLE_DOT)
        self.crossPenDark = wx.Pen(wx.Colour(0, 0, 0), width=1, style=wx.PENSTYLE_SOLID)
        self.crossPenLight = wx.Pen(wx.Colour(255, 255, 255), width=1, style=wx.PENSTYLE_SOLID)
        self.deltafontPen = wx.Pen(self.deltafontcolor, width=1, style=wx.PENSTYLE_SOLID)

        # linewidth, markerstyle and colors for scatter / line plot
        self.markersize = 2
        self.linewidth = 2

        # list of line colors; the color is cycled through the array for each new line or point
        self.linescolor = [wx.Colour(255, 0, 0), wx.Colour(255, 128, 128), wx.Colour(0, 0, 255),
                           wx.Colour(128, 128, 255), wx.Colour(0, 255, 0), wx.Colour(128, 255, 128)]

        # colormap for contour plot
        # each entry consists of a value between 0 (min) and 1 (max) and a color
        # the actual color is generated by linear interpolation between neighboring entries
        # make sure that you sort the entries ascending!
        self.colormap = []
        self.imgcolormap = []    # version for images with reduced color depth (256)
        self.setColormap("rgb")  # initialize colormaps

        # logscale
        self.logx = False
        self.logy = False
        self.logz = False

        # make a tight axis, i.e., use the data's extent for axes
        self.tightx = False
        self.tighty = False

        # axis labels
        self.xlabel = ""
        self.ylabel = ""

        # extensions used for label formatting
        self.ext = ['y', 'z', 'a', 'f', 'p', 'n', 'u', 'm', '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']

    # EVENTS
    def OnEraseBackground(self, event):
        """Event handler for background erase.
        """
        event.Skip()

    def OnPaint(self, event):
        """Event handler for paint event.
        """
        dc = wx.BufferedPaintDC(self)
        self.Draw(dc)

    def OnResize(self, event):
        """Event handler for resize event.
        """
        self.Refresh()

    def OnLMouseDown(self, event):
        """Event handler for left mouse button down. Positions cursor A on the data if the plot is not empty.
        """
        event.Skip()
        # get mouse position in window
        self.mousePos = self.ScreenToClient(wx.GetMousePosition())
        x, y = self.mousePos.Get()

        if len(self.data) == 0:
            return

        # if mouse is in data area, set cursor
        if x > self.dcleft and x < self.dcright and y > self.dctop and y < self.dcbottom:
            self.mouseX1, _ = self.screen2data(x, y)

            # find next line in this direction if the selected trace is not a line
            if self.data_types[self.mouseN] not in ["line", "scatter"]:
                mouseN0 = self.mouseN
                while(1):
                    self.mouseN += 1

                    if self.mouseN < 0:
                        self.mouseN += len(self.data)
                    if self.mouseN >= len(self.data):
                        self.mouseN -= len(self.data)

                    if self.data_types[self.mouseN] in ["line", "scatter"] or self.mouseN == mouseN0:
                        break

    def OnRMouseDown(self, event):
        """Event hanlder for right mouse button down. Positions cursor B on the data if the plot is not empty.
        """
        event.Skip()
        # get mouse position in window
        self.mousePos = self.ScreenToClient(wx.GetMousePosition())
        x, y = self.mousePos.Get()

        if len(self.data) == 0:
            return

        # if mouse is in data area, set cursor
        if x > self.dcleft and x < self.dcright and y > self.dctop and y < self.dcbottom:
            self.mouseX2, _ = self.screen2data(x, y)

            # find next line in this direction if the selected trace is not a line
            if self.data_types[self.mouseN] not in ["line", "scatter"]:
                mouseN0 = self.mouseN
                while(1):
                    self.mouseN += 1

                    if self.mouseN < 0:
                        self.mouseN += len(self.data)
                    if self.mouseN >= len(self.data):
                        self.mouseN -= len(self.data)

                    if self.data_types[self.mouseN] in ["line", "scatter"] or self.mouseN == mouseN0:
                        break

    def OnMouseMove(self, event):
        """Event handler for mouse move event. Updates current position of cursor in data coordinates.
        """
        event.Skip()
        # get mouse position in window
        self.mousePos = self.ScreenToClient(wx.GetMousePosition())
        x, y = self.mousePos.Get()

        # if mouse is in data area, refresh the screen to display the new coordinates
        if x > self.dcleft and x < self.dcright and y > self.dctop and y < self.dcbottom:
            self.mouseIn = True
            self.Refresh()
        else:
            if self.mouseIn:
                self.mouseIn = False
                self.Refresh()

    def OnMouseWheel(self, event):
        """Event handler for mouse wheel event. This event is used to switch the active line / scatter plot for the cursors.
        """
        event.Skip()
        delta = event.GetWheelRotation()

        if len(self.data) == 0:
            return

        # get stepping direction
        d = np.where(delta < 0, -1, 1)

        # find next line in this direction
        mouseN0 = self.mouseN
        while(1):
            self.mouseN += d

            if self.mouseN < 0:
                self.mouseN += len(self.data)
            if self.mouseN >= len(self.data):
                self.mouseN -= len(self.data)

            if self.data_types[self.mouseN] in ["line", "scatter"] or self.mouseN == mouseN0:
                break

        if self.mouseX1 is not None or self.mouseX2 is not None:
            self.Refresh()

    def OnKeyDown(self, event):
        """Event handler for key-press event. Handles the following key strokes:

            - **C**: Clear plot.
            - **X**: Switch between linear and logarithmic scaling on x-axis.
            - **Y**: Switch between linear and logarithmic scaling on y-axis.
            - **Z**: Switch between linear and logarithmic scaling on z-axis. Affects only contour and image plots.
            - **M**: Center cursor A on maxium of active line/scatter plot.
        """
        event.Skip()
        c = chr(min(max(0, event.GetKeyCode()), 255))   # select only ascii range, no special keys

        if c == 'C':    # clear cursors
            self.mouseX1 = None
            self.mouseX2 = None
            self.Refresh()
        elif c == 'X':
            self.logx = not self.logx
            self.contourDCValid = False
            self.Refresh()
        elif c == 'Y':
            self.logy = not self.logy
            self.contourDCValid = False
            self.Refresh()
        elif c == 'Z':
            self.logz = not self.logz
            self.contourDCValid = False
            self.Refresh()
        elif c == 'M':
            if len(self.data) == 0:
                return
            if self.data_types[self.mouseN] in ["line", "scatter"]:
                self.mouseX1 = self.data[self.mouseN][np.argmax(self.data[self.mouseN][:, 1]), 0]
                self.Refresh()

    # DATA HANDLING
    def addImage(self, x, y, z):
        """Add an image plot.

        :param array x: x-axis. Only the min/max values are used and the axis is linearly interpolated.
        :param array y: y-axis. Only the min/max values are used and the axis is linearly interpolated.
        :param array z: Image data, 2d-array.
        :returns: Plot id.
        """
        # get image width and height
        h, w = z.shape
        min, max = np.amin(z), np.amax(z)

        # these are color indices
        c = (((z.flatten() - min) / (max - min)) * 255).astype(int)

        # append to image list
        id = len(self.images)
        self.images.append(wx.BitmapFromBuffer(w, h, self.imgcolormap[c]))

        # append to data list
        id = len(self.data)
        self.data.append(((np.nanmin(x), np.nanmax(x)), (np.nanmin(y), np.nanmax(y)), id))
        self.data_types.append('image')
        self.data_extent.append((np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y)))
        self.Refresh()
        return id

    def addContour(self, x, y, z):
        """Add contour plot.

        :param array x: x-axis of length N. Does not have to be uniform.
        :param array y: y-axis of length M. Does not have to be uniform.
        :param array z: z-data, MxN array.
        :returns: Plot id.
        """
        if(len(x) != z.shape[1]):
            raise ValueError("Length of x and z arrays is not compatible!")
        if(len(y) != z.shape[0]):
            raise ValueError("Length of y and z arrays is not compatible!")

        id = len(self.data)
        self.data.append((x, y, z))
        self.data_types.append('contour')
        self.data_extent.append((np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y)))
        self.contourDCValid = False
        self.Refresh()
        return id

    def addLine(self, x, y):
        """Add a line plot or single point.

        :param array x: x-axis. Can also be a single integer or floating point number.
        :param array y: y-axis data with same shape as x.
        :returns: Plot id.
        """
        if isinstance(x, list) or isinstance(x, np.ndarray):
            if(len(x) != len(y)):
                raise ValueError("Length of x and y arrays is different!")
            nd = np.transpose(np.array([x, y]))
        else:
            nd = np.array([[float(x), float(y)], ])

        id = len(self.data)
        self.data.append(nd)
        self.data_types.append('line')
        self.data_extent.append((np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y)))
        self.Refresh()
        return id

    def addScatter(self, x, y):
        """Add a scatter plot.

        :param array x: x-axis. Can also be a single integer or floating point number.
        :param array y: y-axis data with same shape as x.
        :returns: Plot id.
        """
        id = self.addLine(x, y)
        self.data_types[id] = 'scatter'
        return id

    def setImage(self, id, x, y, z):
        """Overwrite an existing image plot.

        :param int id: Id or index of image plot to overwrite. The plot at the given id must already be an image plot.
        :param array x: x-axis. Only the min/max values are used and the axis is linearly interpolated.
        :param array y: y-axis. Only the min/max values are used and the axis is linearly interpolated.
        :param array z: Image data, 2d-array.
        """
        id = abs(int(id))
        if(id >= len(self.data)):
            raise ValueError("ID of plot element out of range!")
        if(self.data_types[id] != "image"):
            raise ValueError("Element with given ID is not an image plot!")

        # get image width and height
        h, w = z.shape
        min, max = np.amin(z), np.amax(z)

        # these are color indices
        c = (((z.flatten() - min) / (max - min)) * 255).astype(int)

        # overwrite image
        self.images[self.data[id][2]] = wx.BitmapFromBuffer(w, h, self.imgcolormap[c])
        self.data[id] = ((np.nanmin(x), np.nanmax(x)), (np.nanmin(y), np.nanmax(y)), id)
        self.data_extent[id] = (np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y))
        self.Refresh()

    def setContour(self, id, x, y, z):
        """Overwrite an existing contour plot.

        :param int id: Id or index of contour plot to overwrite. The plot at the given id must already be a contour plot.
        :param array x: x-axis of length N. Does not have to be uniform.
        :param array y: y-axis of length M. Does not have to be uniform.
        :param array z: z-data, MxN array.
        """
        if(len(x) != z.shape[1]):
            raise ValueError("Length of x and z arrays is not compatible!")
        if(len(y) != z.shape[0]):
            raise ValueError("Length of y and z arrays is not compatible!")
        id = abs(int(id))
        if(id >= len(self.data)):
            raise ValueError("ID of plot element out of range!")
        if(self.data_types[id] != "contour"):
            raise ValueError("Element with given ID is not a contour plot!")

        nd = (x, y, z)
        self.data[id] = nd
        self.data_extent[id] = (np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y))
        self.contourDCValid = False
        self.Refresh()

    def setLine(self, id, x, y):
        """Overwrite an existing line / scatter plot.

        :param int id: Id or index of line / scatter plot to overwrite. The plot at the given id must already be a line / scatter plot.
        :param array x: x-axis. Can also be a single integer or floating point number.
        :param array y: y-axis data with same shape as x.
        """
        if(len(x) != len(y)):
            raise ValueError("Length of x and y arrays is different!")
        id = abs(int(id))
        if(id >= len(self.data)):
            raise ValueError("ID of plot element out of range!")
        if(self.data_types[id] not in ["line", "scatter"]):
            raise ValueError("Element with given ID is not a line / scatter plot!")
        if isinstance(x, list) or isinstance(x, np.ndarray):
            if(len(x) != len(y)):
                raise ValueError("Length of x and y arrays is different!")
            nd = np.transpose(np.array([x, y]))
        else:
            nd = np.array([[float(x), float(y)], ])

        self.data[id] = nd
        self.data_extent[id] = (np.nanmin(x), np.nanmax(x), np.nanmin(y), np.nanmax(y))
        self.Refresh()

    def setScatter(self, id, x, y):
        """Same as `setLine`.
        """
        self.setLine(id, x, y)

    def getNumberOfPlots(self):
        """Returns total number of plots in this plot window.
        """
        return len(self.data)

    def removeLastPlot(self):
        """Remove last added plot from the stack.
        """
        self.data.pop()
        self.data_extent.pop()
        self.data_types.pop()
        self.Refresh()

    # returns the colormap with given label
    # a colormap consists of two lists, the first containing the supporting points and the second containing the respective r,g,b values
    def setColormap(self, cmap='rainbow'):
        """Activates the colormap with the given label for plotting.

        A colormap consists of a tuple of lists, the first containing the supporting points in the interval 0 to 1 and the second containing the respective r,g,b values as lists.
        For example, the 'rgb' colormap is defined as::

            cmap = ([0,            0.5,         1],
                    [[0, 0, 255], [0, 255, 0], [255, 0, 0]])

        :param mixed cmap: Either name of the colormap or a colormap-defining tuple (default='rgb'). Valid colormap names are 'hot', 'rainbow', 'rgb', 'blue', 'red', 'green', 'rwb' (red-white-blue).
        """
        if isinstance(cmap, str):
            if cmap == "hot":
                self.colormap = ([0, 0.33, 0.66, 1], [[0, 0, 0], [255, 0, 0], [255, 255, 0], [255, 255, 255]])
            elif cmap == "rainbow":
                self.colormap = ([0, 0.2, 0.35, 0.5, 0.65, 0.8, 1], [[150, 0, 200], [0, 0, 255], [0, 255, 255], [0, 255, 0], [255, 255, 0], [255, 128, 0], [255, 0, 0]])
            elif cmap == "rgb":
                self.colormap = ([0, 0.5, 1], [[0, 0, 255], [0, 255, 0], [255, 0, 0]])
            elif cmap == "blue":
                self.colormap = ([0, 1], [[0, 0, 255], [255, 255, 255]])
            elif cmap == "red":
                self.colormap = ([0, 1], [[255, 0, 0], [255, 255, 255]])
            elif cmap == "green":
                self.colormap = ([0, 1], [[0, 255, 0], [255, 255, 255]])
            else:  # red-white-blue
                self.colormap = ([0, 0.5, 1], [[0, 0, 255], [255, 255, 255], [255, 0, 0]])
        elif isinstance(cmap, tuple) or isinstance(cmap, list):
            if len(cmap) != 2 or len(cmap[0]) != len(cmap[1]) or len(cmap[1][0]) != 3:
                print "ERROR: cmap is not a valid colormap."
                return
            self.colormap = cmap
        else:
            print "ERROR: Wrong datatype in setColormap! Has to be string or tuple."
            return

        # prepare colormap for image
        self.imgcolormap = self.getZColor(np.arange(256), min=0, max=256)

        # replot
        self.contourDCValid = False
        self.Refresh()

    def setXLabel(self, label):
        """Set x-axis label.
        """
        self.xlabel = label
        self.Refresh()

    def setYLabel(self, label):
        """Set y-axis label.
        """
        self.ylabel = label
        self.Refresh()

    # adjust min, max of data to get nice looking axes ticks
    # returns new min, max and a list of tickmark positions in data coordinates (real! data coordinates)
    # if logscale = True, min and max are already log10() of data
    def adjustAxis(self, _min, _max, logscale=False):
        """Internally used to adjust min, max and number of ticks to get nice looking axes.

        :param float _min: Minimum data value.
        :param float _max: Maximum data value.
        :param bool logscale: Set to True when axis is using logscale, to adapt the number of ticks (default=False).
        :returns: Suggested min, max and number of ticks.
        """
        ticks = []

        if _min == _max:
            _min, _max = _min - 1, _max + 1

        grossStep = (_max - _min) / 4.0
        step = np.power(10, np.floor(np.log10(grossStep)))
        if step == 0:
            step = 1
        if 5.0 * step < grossStep:
            step = step * 5.0
        elif 2.0 * step < grossStep:
            step = step * 2.0

        _min = np.floor(_min / step) * step
        _max = np.ceil(_max / step) * step

        if logscale:
            # if less than 3 order of magnitude are shown, include sub-ticks
            useSubTicks = (step < 1.0)
            for i in range(int(_min), int(_max + 1), int(np.ceil(step))):
                ticks.append(np.power(10, float(i)))
                if useSubTicks and i < int(_max):
                    for j in range(2, 10):
                        ticks.append(np.float(j) * np.power(10, float(i)))
        else:
            nticks = int(np.ceil(_max / step) - np.floor(_min / step)) + 1
            for i in range(nticks):
                ticks.append(_min + float(i) * step)

        return _min, _max, ticks

    # parse all plot objects and determine the extent of the data x, y axes
    def getDataMinMax(self):
        """Internally used to get the extent of data along x, y and z-axes.
        """
        self.plotXMin = 0
        self.plotXMax = 1
        self.plotYMin = 0
        self.plotYMax = 1
        self.plotZMin = 0
        self.plotZMax = 1

        # there is some data, get min / max
        if self.data:
            self.plotXMin = np.amin(np.array(self.data_extent)[:, 0])
            self.plotXMax = np.amax(np.array(self.data_extent)[:, 1])
            self.plotYMin = np.amin(np.array(self.data_extent)[:, 2])
            self.plotYMax = np.amax(np.array(self.data_extent)[:, 3])
            if self.logx:
                self.plotXMin = np.nan_to_num(np.log10(self.plotXMin))
                self.plotXMax = np.nan_to_num(np.log10(self.plotXMax))
            if self.logy:
                self.plotYMin = np.nan_to_num(np.log10(self.plotYMin))
                self.plotYMax = np.nan_to_num(np.log10(self.plotYMax))

            # check for contour plot for z-range
            if 'contour' in self.data_types:
                zmin = []
                zmax = []
                for i, pl in enumerate(self.data):
                    if self.data_types[i] == "contour":
                        zmin.append(np.nanmin(pl[2]))
                        zmax.append(np.nanmax(pl[2]))
                self.plotZMin = np.nanmin(zmin)
                self.plotZMax = np.nanmax(zmax)
                if self.logz:
                    self.plotZMin = np.nan_to_num(np.log10(self.plotZMin))
                    self.plotZMax = np.nan_to_num(np.log10(self.plotZMax))

                if self.plotZMin == self.plotZMax:
                    self.plotZMin, self.plotZMax = self.plotZMin - 1, self.plotZMax + 1
            if self.plotXMin == self.plotXMax:
                self.plotXMin, self.plotXMax = self.plotXMin - 1, self.plotXMax + 1
            if self.plotYMin == self.plotYMax:
                self.plotYMin, self.plotYMax = self.plotYMin - 1, self.plotYMax + 1

    # get a nice, consistent formatting of the labels
    def formatLabels(self, values, logscale=False):
        """Internally used to get nice, consistent formatting for the tick labels.
        Automatically decides for scientific or floating point notation and uses scientific prefixes to keep number of decimals below 3.

        :param array values: Array of numeric values for which labels are to be generated.
        :param bool logscale: Set to True, when axis uses logscale. This changes the appearance of the labels.
        :returns: An array of strings with label texts.
        """
        txt = []
        if logscale:
            for v in values:
                if np.floor(np.log10(v)) == np.log10(v):
                    txt.append("%.e" % v)
                else:
                    txt.append("")
        else:
            xmax = np.amax(np.absolute(values))
            if xmax < 1e4 and xmax >= 1e-1:
                x = np.array(values)
                fmt = "%%.0f"
                for d in range(5):
                    if np.unique(np.around(x, decimals=d)).shape == x.shape:
                        fmt = "%%.%df" % d
                        break
                for v in x:
                    txt.append(fmt % v)
            else:
                nmax = min(max(np.floor(np.log10(xmax) / 3.0) + 8, 0), len(self.ext) - 1) - 8
                exttxt = self.ext[int(nmax + 8)]

                x = np.array(values) / np.power(1000, nmax)

                fmt = "%%.0f"
                for d in range(5):
                    if np.unique(np.around(x, decimals=d)).shape == x.shape:
                        fmt = "%%.%df%%s" % d
                        break
                for v in x:
                    txt.append(fmt % (v, exttxt))

        return txt

    # same for a single number
    def formatNumber(self, x):
        """Get a formatted number according to the formatting rules that also apply to the labels. Use scientific prefixes and limit the number of decimals below 3.

        :param float x: Number.
        :returns: Formatted string.
        """
        if x == 0.0:
            return "0.0"
        nmax = min(max(np.floor(np.log10(abs(x)) / 3.0) + 8, 0), len(self.ext) - 1) - 8
        exttxt = self.ext[int(nmax + 8)]
        return "%.1f%s" % (x / np.power(1000, nmax), exttxt)

    # returns an interpolated value for alpha
    # alpha is a scalar!
    def interpolateColor(self, alpha):
        """Used internally to calculate the rgb-values for a scalar alpha (0..1) and the currently set colormap.

        :param float alpha: Scalar between 0 and 1.
        :returns: RGB-tuple.
        """
        x1 = np.array(self.colormap[0])
        colors1 = np.array(self.colormap[1], dtype=float)

        if alpha <= x1[0]:
            return colors1[0]
        elif alpha >= x1[-1]:
            return colors1[-1]
        else:
            x2 = np.roll(x1, -1, axis=0)
            colors2 = np.roll(colors1, -1, axis=0)

            A = np.where(alpha >= x1, np.where(alpha <= x2, 1, 0), 0)
            B = ((alpha - x1) / (x2 - x1) * colors2.T + (x2 - alpha) / (x2 - x1) * colors1.T).T
            C = (B.T * A).T

            return np.sum(C, axis=0)

    # get color for z value from colormap; returns r, g, b tuple
    # if min = max, use the data range stored in self.plotZMin / Max
    def getZColor(self, z, min=-1, max=-1):
        """Get RGB-tuples for z-values according to current colormap.

        When `min == max`, the full z-extent of the data is used for mapping.

        :param mixed z: Single z-value, 1d or 2d-array of z-values.
        :param float min: Minimum z value that gets mapped onto 0.
        :param float max: Maximum z value that gets mapped onto 1.
        :returns: RGB-tuples with same shape as z.
        """
        if min == max:
            min = self.plotZMin
            max = self.plotZMax

        # get position in colormap
        a = (z.astype(float) - min) / (max - min)

        if isinstance(a, float):
            return self.interpolateColor(a).astype(np.uint8)
        else:
            col = np.array(map(self.interpolateColor, a.flatten())).astype(np.uint8)
            try:
                return col.reshape(a.shape[0], a.shape[1], 3)
            except:
                return col.reshape(a.shape[0], 3)

    # get mapping prefactors from data to dc space and vice versa
    # min/max values are already in log10 when logscale is used
    def prepareMapping(self):
        """Internally used to prepare the mapping from data to screen coordinates and vice-versa.
        """
        self.map_ax = float(self.dcright - self.dcleft) / float(self.plotXMax - self.plotXMin)
        self.map_bx = float(self.dcleft - self.map_ax * self.plotXMin)
        self.map_ay = float(self.dctop - self.dcbottom) / float(self.plotYMax - self.plotYMin)
        self.map_by = float(self.dcbottom - self.map_ay * self.plotYMin)

    # convert data coordinates to screen coordinates and back
    # screen coordinates are int while data coordinates are float
    # accepts single numbers as well as arrays
    def data2screen(self, x, y):
        """Convert data coordinates x, y to screen coordinates.

        :param mixed x: Single x value or x-axis.
        :param mixed y: Single y value or y-axis with same shape as x.
        :returns: i, j pixel coordinates (integers) with same shapes as x, y.
        """
        if isinstance(x, list):
            x = np.array(x)
            y = np.array(y)
        if self.logx:
            x = np.nan_to_num(np.log10(x))
        if self.logy:
            y = np.nan_to_num(np.log10(y))
        if isinstance(x, np.ndarray):
            return (self.map_ax * x + self.map_bx).astype(int), (self.map_ay * y + self.map_by).astype(int)
        return int(self.map_ax * x + self.map_bx), int(self.map_ay * y + self.map_by)

    def screen2data(self, i, j):
        """Convert screen coordinates i, j to data coordinates.

        :param mixed i: Single i value or i-axis.
        :param mixed j: Single j value or j-axis with same shape as i.
        :returns: x, y data coordinates (float) with same shapes as i, j.
        """
        if isinstance(i, list):
            i = np.array(i)
            j = np.array(j)
        if isinstance(i, np.ndarray):
            x = (i.astype(float) - self.map_bx) / self.map_ax
            y = (j.astype(float) - self.map_by) / self.map_ay
        else:
            x = (float(i) - self.map_bx) / self.map_ax
            y = (float(j) - self.map_by) / self.map_ay

        if self.logx:
            x = np.power(10, x)
        if self.logy:
            y = np.power(10, y)
        return x, y

    # DRAWING FUNCTIONS
    def Draw(self, dc):
        """Internally used to draw the plots to a device context (dc).
        Plotting order is contour plots first, followed by image plots and line / scatter plots and axes, labels and cursors.
        """
        # Get the actual client size of ourselves
        self.dcwidth, self.dcheight = self.GetClientSize()
        if not self.dcwidth or not self.dcheight:
            return

        # set text properties
        dc.SetFont(self.font)
        dc.SetTextBackground(self.bgcolor)
        dc.SetTextForeground(self.axiscolor)

        # get extent of data and adjust ticks to get nice axes
        self.getDataMinMax()
        if self.tightx:
            _, _, self.XTicks = self.adjustAxis(self.plotXMin, self.plotXMax, self.logx)
        else:
            self.plotXMin, self.plotXMax, self.XTicks = self.adjustAxis(self.plotXMin, self.plotXMax, self.logx)

        if self.tighty:
            _, _, self.YTicks = self.adjustAxis(self.plotYMin, self.plotYMax, self.logy)
        else:
            self.plotYMin, self.plotYMax, self.YTicks = self.adjustAxis(self.plotYMin, self.plotYMax, self.logy)

        # format labels
        self.lblx = self.formatLabels(self.XTicks, self.logx)
        self.lbly = self.formatLabels(self.YTicks, self.logy)

        # get label sizes
        lblwidth = 0
        for l in self.lbly:
            tmp, _ = dc.GetTextExtent(l)
            if tmp > lblwidth:
                lblwidth = tmp
        _, lblheight = dc.GetTextExtent("Text")

        # determine optimal margins
        self.bottommargin = 2 * lblheight
        if(self.xlabel != ""):
            self.bottommargin += lblheight
        self.leftmargin = lblheight + lblwidth
        if(self.ylabel != ""):
            self.leftmargin += lblheight

        # get coordinates of plot area in dc
        self.dcleft = self.leftmargin
        self.dctop = 2 * lblheight
        self.dcright = self.dcwidth - lblheight
        self.dcbottom = self.dcheight - self.bottommargin

        # now prepare mapping prefactors between data and screen
        self.prepareMapping()

        # erase dc by filling with background color
        dc.SetBackground(wx.Brush(self.bgcolor, wx.SOLID))
        dc.Clear()

        # plot all contour plots FIRST
        # this is important as this is the image that gets stored in the memoryDC
        if 'contour' in self.data_types:
            if not self.contourDCValid:
                for i, d in enumerate(self.data):
                    if self.data_types[i] == "contour":
                        self.drawContour(dc, d)

                # clear old bitmap
                self.contourDC.SelectObject(wx.NullBitmap)
                # create new bitmap
                bmp = wx.EmptyBitmap(self.dcright - self.dcleft + 1, self.dcbottom - self.dctop + 1)
                self.contourDC.SelectObject(bmp)
                # copy dc data
                self.contourDC.Blit(0, 0, self.dcright - self.dcleft + 1, self.dcbottom - self.dctop + 1, dc, self.dcleft, self.dctop)

                self.contourDCValid = True
            else:
                wsrc, hsrc = self.contourDC.GetSize()
                dc.StretchBlit(self.dcleft, self.dctop, self.dcright - self.dcleft + 1, self.dcbottom - self.dctop + 1, self.contourDC, 0, 0, wsrc, hsrc)

        # now plot all images
        if 'image' in self.data_types:
            for i, d in enumerate(self.data):
                if self.data_types[i] == "image":
                    self.drawImage(dc, d)

        # now plot all line plots
        if 'line' in self.data_types or 'scatter' in self.data_types:
            self.lineColorIter = itertools.cycle(self.linescolor)    # reset the iterator
            for i, d in enumerate(self.data):
                if self.data_types[i] == "line" or self.data_types[i] == "scatter":
                    self.drawLine(dc, d, self.data_types[i], (self.mouseN == i))

        # finally plot the axes
        self.drawAxes(dc)

    def drawImage(self, dc, img):
        """Internally used to draw an image (img) to a device context (dc).
        """
        # set up a dcclipper to constrain the lineart to the plot area
        wx.DCClipper(dc, self.dcleft, self.dctop, self.dcright - self.dcleft + 1, self.dcbottom - self.dctop + 1)

        # create a memory DC from the stored bitmap
        memdc = wx.MemoryDC()
        memdc.SelectObject(self.images[img[2]])
        wsrc, hsrc = memdc.GetSize()

        # get destination coordinates on screen
        x0, y0 = self.data2screen(img[0][0], img[1][0])
        x1, y1 = self.data2screen(img[0][1], img[1][1])

        # copy
        dc.StretchBlit(x0, y0, x1 - x0, y1 - y0, memdc, 0, 0, wsrc, hsrc)

        # destroy memoryDC
        memdc.SelectObject(wx.NullBitmap)

    def drawAxes(self, dc):
        """Internally used to draw the axes plus labels. Takes also care of crosshair, mouse coordinates and delta.
        """
        # make ticks along x axes
        x = []
        for t in self.XTicks:
            xs, _ = self.data2screen(t, 1)
            x.append(xs)
        y = []
        for t in self.YTicks:
            _, ys = self.data2screen(1, t)
            y.append(ys)

        # draw grid
        if self.showGrid:
            dc.SetPen(self.gridPen)
            for i in range(len(x)):
                if x[i] >= self.dcleft and x[i] <= self.dcright:
                    dc.DrawLine(x[i], self.dctop, x[i], self.dcbottom)
            for i in range(len(y)):
                if y[i] >= self.dctop and y[i] <= self.dcbottom:
                    dc.DrawLine(self.dcleft, y[i], self.dcright, y[i])

        # finish tickmarks
        dc.SetPen(self.axisPen)
        for i in range(len(x)):
            if x[i] >= self.dcleft and x[i] <= self.dcright:
                dc.DrawLine(x[i], self.dcbottom, x[i], self.dcbottom - self.ticklength)
                dc.DrawLine(x[i], self.dctop, x[i], self.dctop + self.ticklength)
                txtW, txtH = dc.GetTextExtent(self.lblx[i])
                dc.DrawText(self.lblx[i], x[i] - txtW / 2, self.dcbottom + txtH / 2)
        for i in range(len(y)):
            if y[i] >= self.dctop and y[i] <= self.dcbottom:
                dc.DrawLine(self.dcleft, y[i], self.dcleft + self.ticklength, y[i])
                dc.DrawLine(self.dcright, y[i], self.dcright - self.ticklength, y[i])
                txtW, txtH = dc.GetTextExtent(self.lbly[i])
                dc.DrawText(self.lbly[i], self.dcleft - txtW - txtH / 2, y[i] - txtH / 2)

        # make a nice box around
        dc.DrawLine(self.dcleft, self.dctop, self.dcleft, self.dcbottom)
        dc.DrawLine(self.dcleft, self.dcbottom, self.dcright, self.dcbottom)
        dc.DrawLine(self.dcright, self.dcbottom, self.dcright, self.dctop)
        dc.DrawLine(self.dcright, self.dctop, self.dcleft, self.dctop)

        # write axis labels
        if self.xlabel != "":
            txtW, txtH = dc.GetTextExtent(self.xlabel)
            dc.DrawText(self.xlabel, (self.dcleft + self.dcright) / 2 - txtW / 2, self.dcheight - 3 * txtH / 2)
        if self.ylabel != "":
            txtW, txtH = dc.GetTextExtent(self.ylabel)
            dc.DrawRotatedText(self.ylabel, txtH / 2, (self.dctop + self.dcbottom) / 2 + txtW / 2, 90)

        # display mouse coordinates
        mx, my = self.mousePos.Get()
        ix, iy = self.screen2data(mx, my)
        txt = "(" + self.formatNumber(ix) + ", " + self.formatNumber(iy) + ")"
        txtW, txtH = dc.GetTextExtent(txt)
        dc.DrawText(txt, self.dcleft, self.dctop - txtH - 3)

        # if show cross, draw cross through mouse position
        if self.showCross and self.mouseIn:
            dc.SetPen(self.crossPenDark)
            dc.DrawLine(self.dcleft, my, self.dcright, my)
            dc.DrawLine(mx, self.dctop, mx, self.dcbottom)
            dc.SetPen(self.crossPenLight)
            dc.DrawLine(mx + 1, self.dctop, mx + 1, self.dcbottom)
            dc.DrawLine(self.dcleft, my + 1, self.dcright, my + 1)

        # write delta of cursors?
        # this is the last part of the drawing routine as it changes the default font
        if self.mouseX1 is not None and self.mouseX2 is not None:
            dc.SetTextForeground(self.deltafontcolor)
            dc.SetFont(self.deltafont)
            txt = "A-B = " + self.formatNumber(self.cursor1[1] - self.cursor2[1])
            txtW, txtH = dc.GetTextExtent(txt)
            dc.DrawText(txt, self.dcright - txtW - 5, self.dctop - txtH - 5)

    def drawLine(self, dc, data, type='line', cursors=False):
        """Used internally to draw a line/scatter plot (data, type) to a device context (dc).
        If cursors is True, draw cursors accordingly.
        """
        # create pen
        color = next(self.lineColorIter)
        dc.SetPen(wx.Pen(color, width=self.linewidth, style=wx.PENSTYLE_SOLID))
        dc.SetBrush(wx.Brush(color))

        if cursors:
            if self.mouseX1 is not None:
                self.cursor1 = self.drawCursor(dc, data, self.mouseX1, "A")
            if self.mouseX2 is not None:
                self.cursor2 = self.drawCursor(dc, data, self.mouseX2, "B")

        # set up a dcclipper to constrain the lineart to the plot area
        wx.DCClipper(dc, self.dcleft, self.dctop, self.dcright - self.dcleft, self.dcbottom - self.dctop)

        x, y = self.data2screen(*(np.array(data).T))
        N = len(x)

        # if length = 1 or type is scatter, draw a point
        if type == 'scatter' or N == 1:
            for i in range(N):
                dc.DrawCircle(x[i], y[i], self.markersize)
        else:    # draw line
            for i in range(N - 1):
                dc.DrawLine(x[i], y[i], x[i + 1], y[i + 1])

    def drawCursor(self, dc, data, x, label):
        """Used internally to draw cursors.
        """
        # get data coordinates - limit cursor to valid data range
        if x <= np.amin(data[:, 0]):
            x = np.amin(data[:, 0])
            y = data[np.argmin(data[:, 0]), 1]
        elif x >= np.amax(data[:, 0]):
            x = np.amax(data[:, 0])
            y = data[np.argmax(data[:, 0]), 1]
        else:
            i0 = np.argmin(np.absolute(data[:, 0] - x))
            y = (data[i0 + 1, 1] - data[i0, 1]) / (data[i0 + 1, 0] - data[i0, 0]) * (x - data[i0, 0]) + data[i0, 1]

        # go back to screen coordinates
        i, j = self.data2screen(x, y)

        # draw cursor
        oldpen = dc.GetPen()
        dc.DrawLine(i, self.dcbottom, i, self.dctop)
        dc.DrawLine(i - 5, j - 5, i + 5, j + 5)
        dc.DrawLine(i - 5, j + 5, i + 5, j - 5)
        dc.SetPen(wx.Pen(wx.Colour(0, 0, 0), width=self.linewidth, style=wx.PENSTYLE_DOT))
        dc.DrawLine(i, self.dcbottom, i, self.dctop)
        dc.DrawLine(i - 5, j - 5, i + 5, j + 5)
        dc.DrawLine(i - 5, j + 5, i + 5, j - 5)
        dc.SetPen(oldpen)

        txtW, txtH = dc.GetTextExtent(label)
        dc.DrawText(label, i - txtW - 5, self.dctop + 10)
        txt = self.formatNumber(y) + " @ " + self.formatNumber(x)
        dc.DrawText(txt, i + 5, self.dctop + 10)

        return x, y

    def drawContour(self, dc, cont):
        """Used internally to draw a contour plot (cont) to a device context (dc).
        `cont` is a tuple consisting of x-axis, y-axis and z-data (2d).
        """
        Nx, Ny = len(cont[0]), len(cont[1])
        x, y, z = cont
        x, y = self.data2screen(x, y)

        # set up a dcclipper to constrain the plot to the plot area
        wx.DCClipper(dc, self.dcleft, self.dctop, self.dcright - self.dcleft, self.dcbottom - self.dctop)

        zavg = 0.25 * (z + np.roll(z, -1, axis=0) + np.roll(z, -1, axis=1) + np.roll(np.roll(z, -1, axis=0), -1, axis=0))
        if self.logz:
            zavg = np.nan_to_num(np.log10(zavg))
        cols = self.getZColor(zavg)

        for i in range(Nx - 1):
            for j in range(Ny - 1):

                x0, y0 = x[i], y[j]
                x1, y1 = x[i + 1], y[j + 1]
                if x0 > x1:
                    x0, x1 = x1, x0
                if y0 > y1:
                    y0, y1 = y1, y0

                color = wx.Colour(*cols[j, i])
                dc.SetPen(wx.Pen(color, width=self.linewidth, style=wx.PENSTYLE_SOLID))
                if x1 - x0 < 2:
                    if y1 - y0 < 2:
                        dc.DrawPoint(x0, y0)
                    else:
                        dc.DrawLine(x0, y0, x0, y1)
                else:
                    if y1 - y0 < 2:
                        dc.DrawLine(x0, y0, x1, y0)
                    else:
                        dc.SetBrush(wx.Brush(color))
                        dc.DrawRectangle(x0, y0, x1 - x0 + 1, y1 - y0 + 1)


# simple plot window with a single plot canvas
class PlotFrame(wx.Frame):
    """A simple plot window containing a single plot canvas which can be accessed as `plotCanvas`.
    """
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.plotCanvas = FSRSPlot(self)


# plot window with two canvases in a vertical splitter window
class DualPlotFrame(wx.Frame):
    """A simple plot window containing a two vertically stacked plot canvases.
    The upper / lower one can be accessed as `upperPlotCanvas` and `lowerPlotCanvas`.
    """
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        size = self.GetClientSize()
        self.splitter = wx.SplitterWindow(self, style=wx.SP_3DSASH | wx.SP_NOBORDER)
        self.upperPlotCanvas = FSRSPlot(self.splitter)
        self.lowerPlotCanvas = FSRSPlot(self.splitter)
        self.splitter.SplitHorizontally(self.upperPlotCanvas, self.lowerPlotCanvas, sashPosition=size[1] / 2)

# ----------------------------------------------------------------------------------------------------------------------------
# for development
if __name__ == '__main__':
    # setup a wxPython app
    app = wx.App()

    # get an instance of a plot frame
    frame = PlotFrame(None, title="pyFSRS - Test plot panel", size=(640, 480))
    frame.Show()
    frame.plotCanvas.setColormap("blue")

    # get some nice data
    x = np.linspace(-10, 10, 64)
    y = np.linspace(-10, 10, 64)

    X, Y = np.meshgrid(x, y)
    z = np.exp(-(X**2 +Y**2) / 5.0**2) * np.sin(X)
    frame.plotCanvas.addImage(x, y, z)
#    frame.plotCanvas.addLine(x, -5 + 10.0 * np.exp(-x**2 / 5.0**2))

    # show frame and start app
    app.MainLoop()
