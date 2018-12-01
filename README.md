pyFSRS - Femtosecond Stimulated Raman Spectroscopy Made Easy!
=============================================================


pyFSRS is a modular GUI for pump-probe-type optical experiments, specialized for
femtosecond stimulated Raman spectroscopy and transient-absorption spectroscopy.
However, it is not limited to these two applications and can be directly used for
any other pump-probe experiment without modification.

If you are interested in the technical and scientific details of FSRS, I recommend the following three papers as a starting point:

* Dietze and Mathies, *ChemPhysChem* **17**, 1224 (2016).
* McCamant et al., *Appl. Spectrosc.* **57**, 1317 (2003).
* McCamant et al., *Rev. Sci. Instrum.* **75**, 4971 (2004).

The architecture of the program is modular and open, so that anyone can modify it according
to his/her needs: The pyFSRS GUI is fully modular, i.e., all devices and measurement modi are
incorporated as modules that are loaded dynamically at startup. Therefore, extending pyFSRS is as easy
as creating a new subclass from `FSRSModule` and placing it in the `installed_modules` folder. The only
restriction is that each class has to be in its own file having the identical filename as the class name.
For example, `myClass` should be placed in a file called `myClass.py`.

Video Tutorial
============

A short video tutorial of installation and features.
https://youtu.be/-cuXmEfwrig

Installation
============

install with 'python pyfsrs-installer.py' to get the correct python libraries

In order to use pyFSRS, first make sure that all the prerequisites are met.
Then download and unpack the zip archive and execute the main file *pyFSRS.py* using python.

I have tested/developed this program using Python 2.7 and Windows xp, 7,8 and 10.

Prerequisites:
--------------

To run the bare GUI, you need the following modules installed:
   If your python libraries are too old or too new many of the functions 
   will break. Thus we recommend staying with these versions.

* **wxPython**: (Version 4.0.1) The GUI is built on wxPython.
* **numpy**: (Version 1.14.5) Experimental data are stored and manipulated as numpy.arrays.

For the XCScan module, you also need:

* **scipy**: (Version 1.0.0) Fitting of cross-correlation data with Gaussians.

For the devices, there are additional specific dependencies that have to be met:

* **pyVISA**: (Version 1.9.0) GPIB devices like lock-ins or stage controllers.
* **PyDAQmx**: (Not Maintained) National Instruments DAQ boards for in- and output (for shutters or stepper motors).
* **PICam library**: (Static) Princeton Instruments PICam compatible cameras.

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
