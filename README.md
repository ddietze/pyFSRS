pyFSRS - Femtosecond Stimulated Raman Spectroscopy Made Easy!
=============================================================

pyFSRS is a modular GUI for pump-probe-type optical experiments, specialized for
femtosecond stimulated Raman spectroscopy and transient-absorption spectroscopy.
However, it is not limited to these two applications and can be directly used for
any other pump-probe experiment without modification.

The architecture of the program is modular and open, so that anyone can modify it according
to his/her needs: The pyFSRS GUI is fully modular, i.e., all devices and measurement modi are 
incorporated as modules that are loaded dynamically at startup. Therefore, extending pyFSRS is as easy 
as creating a new subclass from `FSRSModule` and placing it in the `installed_modules` folder. The only 
restriction is that each class has to be in its own file having the identical filename as the class name. 
For example, `myClass` should be placed in a file called `myClass.py`.

Installation
============

There is no installation routine / setup file yet.
In order to use pyFSRS, first make sure that all the prerequisites are met.
Then download and unpack the zip archive and execute the main file *pyFSRS.py* using python.

I have tested/developed this program using Python 2.7 and Windows.

Prerequisites:
--------------

To run the bare GUI, you need the following modules installed:

* **wxPython**: The GUI is built on wxPython.
* **numpy**: Experimental data are stored and manipulated as numpy.arrays.

For the XCScan module, you also need:

* **scipy**: Fitting of cross-correlation data with Gaussians.

For the devices, there are additional specific dependencies that have to be met:

* **pyVISA**: GPIB devices like lock-ins or stage controllers.
* **PyDAQmx**: National Instruments DAQ boards for in- and output (for shutters or stepper motors).
* **PICam library**: Princeton Instruments PICam compatible cameras.

Documentation
=============

A full documentation of the program can be found on my GitHub Pages: <http://ddietze.github.io/pyFSRS>.

Licence
=======

This program is free software: you can redistribute and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2014-2016 Daniel Dietze <daniel.dietze@berkeley.edu>.
