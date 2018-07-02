"""
.. module: pyFSRS-installer
   :platform: Windows
.. moduleauthor:: Scott R. Ellis <skellis@berkeley.edu>

pyFSRS is a modular GUI for pump-probe-type optical experiments, specialized for
femtosecond stimulated Raman spectroscopy and transient-absorption spectroscopy.
However, it is not limited to these two applications and can be directly used for
any other pump-probe experiment without modification.

The architecture of the program is modular and open, so that anyone can modify it according
to his / her needs.

..
   This file is an installer of the library required to run the pyFSRS app. 
   If your python libraries are too old or too new many of the functions 
   will break. Thus we recommend staying with these versions.

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

import os

def installNumpy():
	try:
		import numpy as np
		npversion= np.version.version
		if npversion == "1.14.5":
			print "numpy version is up to date."
		else:
			print "scipy version is up not preferable for this software. Installing version 1.14.5:"
			os.system("pip install -U numpy==1.14.5")

	except ImportError:
		print "numpy is not installed. Installing version 1.14.5:"
		os.system("pip install -U numpy==1.14.5")


def installScipy():
	try:
		import scipy
		scipyversion= scipy.version.version
		if scipyversion == "1.0.0":
			print "scipy version is up to date."
		else:
			print "scipy version is up not preferable for this software. Installing version 1.0.0:"
			os.system("pip install -U scipy==1.0.0")

	except ImportError:
		print "scipy is not installed. Installing version 1.0.0:"
		os.system("pip install -U scipy==1.0.0")


def installWX():
	try:
		import wx
		wxversion= wx.__version__
		if wxversion == "4.0.1":
			print "wx version is up to date."
		else:
			print "wx version is up not preferable. Installing version 4.0.1:"
			os.system("pip install -U wx==4.0.1")

	except ImportError:
		print "wx is not installed. Installing version 4.0.1:"
		os.system("pip install -U wx==4.0.1")

def installVisa():
	try:
		import visa
		visaversion= visa.__version__
		if visaversion == "1.9.0":
			print "visa version is up to date."
		else:
			print "visa version is up not preferable. Installing version 1.9.0:"
			os.system("pip install -U visa")
	except ImportError:
		print "visa is not installed. Installing version 1.9.0:"
		os.system("pip install -U visa")




installNumpy()
installScipy()
installWX()
installVisa()