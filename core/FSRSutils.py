"""
.. module: FSRSutils
   :platform: Windows
.. moduleauthor:: Daniel R. Dietze <daniel.dietze@berkeley.edu>

This module provides some utility functions that are used internally in pyFSRS.

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


# append stage parameters to a property dictionary
# stage parameters are: start, stop, step size, log/lin scale
def appendStageParameters(prop, fr=-500, to=2500, st=20):
    """Create and append the necessary controls for a delay stage to a FSRSmodule property dictionary.

    This function creates the following controls:

        - **From (fs)** (textbox): Set the starting position. When value changes, `onAxisRangeChange` is called (has to be implemented by user).
        - **Till (fs)** (textbox): Set the ending position. When value changes, `onAxisRangeChange` is called (has to be implemented by user).
        - **Step Size (fs)** / **# of Steps** (textbox): Set the desired step size (linear stepping) or number of steps (logarithmic stepping). When value changes, `onAxisRangeChange` is called (has to be implemented by user).
        - **Mode** (choice): Set type of stepping ('linear', 'logarithmic', 'from file'). When value changes, `onAxisRangeChange` is called (has to be implemented by user).
        - **Random** (checkbox): If True, the target positions are approached in random order, otherwise sequential. Works for all modes.
        - **Use File** (fie picker): Select a text file containing the desired stage positions. If there are several columns in the file, only the first one is used.

    :param dict prop: Property dictionary to which the controls are appended.
    :param float fr: Initial start position in fs (default=-500).
    :param float to: Initial stop position in fs (default=2500).
    :param float st: Initial step size in fs (default=20).
    :returns: Appended property dictionary.
    """
    prop.append({"label": "From (fs)", "type": "input", "value": str(fr), "info": "float", "event": "onAxisRangeChange"})
    prop.append({"label": "Till (fs)", "type": "input", "value": str(to), "info": "float", "event": "onAxisRangeChange"})
    prop.append({"label": "Step Size (fs)", "type": "input", "value": str(st), "info": "float", "event": "onAxisRangeChange"})
    prop.append({"label": "Mode", "type": "choice", "choices": ["linear", "logarithmic", "from file"], "value": 0, "event": "onAxisRangeChange"})
    prop.append({"label": "Random", "type": "checkbox", "value": 0, "info": "randomize steps"})
    prop.append({"label": "Use File", "type": "file", "value": "", "info": "open"})
    return prop


# call this event handler within the experiment class employing the stage parameters
def onAxisRangeChange(self, event):
    """Handles changes in one of the axis parameters.

    Call this event handler from within an event handler of the same name in the module using the stage.
    """
    event.Skip()        # important to ensure proper function of text ctrl

    mode = self.getPropertyByLabel("mode").getValue()
    start = float(self.getPropertyByLabel("from").getValue())
    stop = float(self.getPropertyByLabel("till").getValue())
    steps = float(self.getPropertyByLabel("step").getValue())        # this accounts both for "step size" and "# of steps"

    # log scale - number of steps
    if mode == 1:  # log
        self.getPropertyByLabel("step").setLabel("# of Steps")

        start = np.power(10, np.nan_to_num(np.log10(start)))
        stop = np.power(10, np.nan_to_num(np.log10(stop)))
        steps = abs(steps)    # this number should be positive

    elif mode == 0:    # lin scale
        self.getPropertyByLabel("step").setLabel("Step Size (fs)")

        N = max(2, int(abs(stop - start) / abs(steps) + 1))
        stop = (N - 1) * steps + start    # adjust end point to match step size; step size can be negative

    self.getPropertyByLabel("from").setValue(str(start))
    self.getPropertyByLabel("till").setValue(str(stop))
    self.getPropertyByLabel("step").setValue(str(steps))


# returns a list of time points using the given parameters
def prepareScanPoints(self):
    """Returns a list of stage positions according to the current stage settings.

    Call from within the module using the stage as this function directly reads the stage settings from the module properties.
    """
    mode = self.getPropertyByLabel("mode").getValue()
    start = float(self.getPropertyByLabel("from").getValue())
    stop = float(self.getPropertyByLabel("till").getValue())
    steps = float(self.getPropertyByLabel("step").getValue())

    points = []

    if mode == 1:    # log
        points = np.logspace(np.log10(start), np.log10(stop), steps)

    elif mode == 0:    # lin
        N = max(2, int(abs(stop - start) / abs(steps) + 1))
        points = np.linspace(start, stop, N)

    else:
        print "load", self.getPropertyByLabel("use file").getValue()
        if self.getPropertyByLabel("use file").getValue() != "":    # load from file
            points = np.loadtxt(self.getPropertyByLabel("use file").getValue(), unpack=True)
            if len(points.shape) > 1:    # got several columns
                points = points[0]

    if self.getPropertyByLabel("random").getValue():
        np.random.shuffle(points)

    return points


# shortcut to save multicolumn data
def saveFSRS(filename, data):
    """Shortcut to save N-column data using numpy's `savetxt`.

    :param str filename: Filename of output file.
    :param array data: N x M data array.
    """
    np.savetxt(filename, np.transpose(data), delimiter="\t")


# save cross correlation data
# the first column is the time delay in fs
# the other columns correspond to the wavelengths of the spectrograph
def saveXC(filename, timepoints, data):
    """Shortcut to save cross correlation data using numpy's `savetxt`.

    :param str filename: Filename of output file.
    :param array timepoints: M-dim. array of stage positions = time axis.
    :param array data: N x M data array.
    """
    d = np.transpose(np.vstack([timepoints, np.transpose(data)]))
    np.savetxt(filename, d, delimiter="\t")


# use the historically correct formatting for FSRS and TA data filenames
def formatFSRSFilename(type, basename, step, set=0, shutter=0):
    """Use the historical formatting convention for FSRS and TA data filenames.

    The generated filenames are compatible with the formerly used LabView code in the Mathies lab.
    This function is called by the FSRS-modules.

    :param int type: Type of spectrum (0 = FSRS, 1 = TA).
    :param str basename: Basename of the generated files.
    :param float step: Position of axis = time.
    :param int set: Number of measurement set or run (default = 0).
    :param int shutter: State of actinic shutter (0 = closed = ground state, 1 = open = excited state).
    :returns: Formatted filename: basename_(p/m)|step|(gr/exc/_)set.
    """
    name = basename + "_"
    if step > 0:
        name += "p"
    elif step < 0:
        name += "m"
    elif step == 0 and (shutter == 1 or type == 1):
        name += "m"

    name += str(abs(int(step)))

    if type == 0:    # FSRS
        if shutter == 0:    # closed = gr
            name += "gr"
        else:
            name += "exc"

    else:    # TA and dT/T
        name += "_"

    name += str(set)
    return name
