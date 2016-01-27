"""
.. module: pyFSRS
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

pyFSRS is a modular GUI for pump-probe-type optical experiments, specialized for
femtosecond stimulated Raman spectroscopy and transient-absorption spectroscopy.
However, it is not limited to these two applications and can be directly used for
any other pump-probe experiment without modification.

The architecture of the program is modular and open, so that anyone can modify it according
to his / her needs.

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
import glob
import os

# import my pyFSRS modules
import core.FSRSModule
import core.ModulePanel as FSM


# main class
class pyFSRS(wx.Frame):
    """Main window of the pyFSRS application.
    """

    def __init__(self, parent, title):
        super(pyFSRS, self).__init__(parent, title=title, pos=(3, 3))
        self.SetMinSize((400, 0.95 * wx.GetDisplaySize()[1]))

        # load all modules
        self.loadModules()

        # build the main GUI
        self.createUI()

        # make modules aware of their fellows
        self.initializeModules()

        # set working directory
        self.default_path = "."         #: Initial default path for save dialog boxes. Set to your preferred data directory.
        os.chdir(os.path.abspath(self.default_path))

        # bind the app exit event to an event handler so we can check whether there are some experiments running and shut down all the modules properly
        self.Bind(wx.EVT_CLOSE, self.onQuit)

        # display myself
        self.Fit()

        self.Show()


    def loadModules(self):
        """Load all modules that are available in subfolders of the folder *installed_modules*.

        The names of the subfolders give the name of the category.
        The names of the modules have to be equal to the name of the module's python file and the name of the class.
        """
        self.modules = []
        self.categories = []

        # load modules
        folders = sorted(glob.glob("installed_modules/*"))
        for c in folders:
            catName = os.path.split(c)[-1]
            list = sorted(glob.glob(c + "/*.py"))

            found = False
            for d in list:
                print d
                if os.path.split(d)[-1] != "__init__.py":
                    try:
                        cll = core.FSRSModule.load_from_file(d)

                        for cl in cll:
                            cl.category = catName
                            print "added module", cl.name

                        self.modules = self.modules + cll
                        found = True
                    except:
                        raise
                        # pass    # ignore modules that cannot be loaded, e.g. due to missing libraries
            if found:
                self.categories.append(catName)


    def createUI(self):
        """Create user interface according the the available modules.
        """
        # create a notebook widget to hold the different categories
        self.notebook = wx.Notebook(self, -1, style=wx.LEFT)

        # populate tree - create categories
        for c in self.categories:

            # create new FSRS module page
            page = FSM.ModulePage(self.notebook, -1)

            # add modules
            for m in self.modules:
                if m.category == c:

                    # create new module panel
                    mp = FSM.ModulePanel(page, -1, label=m.name)

                    # get widget pane to place the widgets
                    mpp = mp.GetPanel()

                    # for each module, create the properties and add to the widget panel
                    for p in m.properties:
                        wnd = p.createHandle(mpp)
                        p.setLabelWnd(mp.Add(p.getLabel(), wnd=wnd))

                    # add panel to notebook page
                    page.AddPanel(mp)

            # now add page to notebook
            self.notebook.AddPage(page, c)

        # some layouting
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.notebook.SetBackgroundColour(wx.Colour(255, 255, 255))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND, 0)
        self.SetSizer(sizer)


    def initializeModules(self):
        """Initialize available modules.

        This function calls the `initialize` function of each module and passes along a list of all available modules, so that each module may be aware of its fellow modules.
        """
        for m in self.modules:
            m.initialize(self.modules)

    # -------------------------------------------------------------------------------------------------------------------
    # main events
    def onQuit(self, event):
        """Handle quit events.

        Asks each module if the program may quit.
        """
        if event.CanVeto() and len(self.modules) > 0:
            veto = False
            for m in self.modules:
                veto = veto | (not m.canQuit())
            if veto:
                event.StopPropagation()
            else:
                self.onExitApp(event)
        else:
            self.onExitApp(event)

    def onExitApp(self, event):
        """This function really quits the app.

        Calls the `shutdown` function of each module to ensure a proper exit.
        """
        if len(self.modules) > 0:
            for m in self.modules:
                m.shutdown
        self.Destroy()

if __name__ == '__main__':
    app = wx.App()
    pyFSRS(None, title="pyFSRS - (c) D. Dietze, 2014-2016")
    app.MainLoop()
