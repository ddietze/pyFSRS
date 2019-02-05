"""
.. module: dummySensor
   :platform: Windows
.. moduleauthor:: Scott R. Ellis <skellis@berkeley.edu>

dummyDAQ provides a dummy input device for testing purposes.
You can use this file as a starting point when writing your own input device module for pyFSRS.

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
import time
import numpy as np
import core.FSRSModule as module
import core.Optutils as outils




def rosenbrock_val(coord,*params):
    """
    evaluates rosenbrock's function in any dimension. the minimum is found at (x,y)=(a,a^2) traditionally a is set to 1 while b is set to 100.
    Parameters
    --------------
    coord : np.array(dtype=float)
        ``an N dimensional numpy array to be evaluated by Rosenbrocks function.
    params : float
        ``optional positional parameters of lenght 2N which are to be the coefficients of 
        Rosenbrock's value. default is a=1 b=100
    Returns
    -------
    val : float
        value of rosenbrock's function at the given coord.
    Notes
    --------
    https://en.wikipedia.org/wiki/Rosenbrock_function
    Examples
    ---------
    >>> print rosenbrock_val([1,1,1])
    [0]

    """
    coord=np.array(coord).T
    val =0
    if len(params)==2*(len(coord)-1):
        for i in range(0, len(coord)-1):
            val+= (params[2*i]-coord[i])**2+params[2*i+1]*(coord[i+1]-coord[i]**2)**2
    else:
        for i in range(0, len(coord)-1):
            val+= (1-coord[i])**2+100*(coord[i+1]-coord[i]**2)**2
    return val

def parabola_val(coord,*params):
    """
    evaluates a parabola's function in any dimension. the minimum is found at (x,y)=(1,1) unless alternative parameters are found
    Parameters
    --------------
    coord : np.array(dtype=float)
        ``an N dimensional numpy array to be evaluated.
    params : float
        ``optional positional parameters of lenght N which are to be the coefficients of 
        Minimum of the parabola default is (1,1)
    Returns
    -------
    val : float
        value of rosenbrock's function at the given coord.
    Notes
    --------
    https://en.wikipedia.org/wiki/Test_functions_for_optimization
    Examples
    ---------
    >>> print rosenbrock_val([1,1,1])
    [0]

    """
    coord=np.array(coord).T
    val =0
    if len(params)==len(coord):
        for i in range(0, len(coord)):
            val+= (coord[i]-params[i])**2
    else:
        for i in range(0, len(coord)):
            val+= (coord[i]-1)**2
    return val

def ackley_val(coord):
    """
    evaluates a ackley's function in 2 dimensions. the minimum is found at (x,y)=(1,1) unless alternative parameters are found
    Parameters
    --------------
    coord : np.array(dtype=float)
        ``an N dimensional numpy array to be evaluated.
    params : float
        ``optional positional parameters of lenght N which are to be the coefficients of 
        Minimum of the parabola default is (1,1)
    Returns
    -------
    val : float
        value of rosenbrock's function at the given coord.
    Notes
    --------
    https://en.wikipedia.org/wiki/Test_functions_for_optimization
    Examples
    ---------
    >>> print rosenbrock_val([1,1,1])
    [0]

    """

    coord=np.array(coord).T
    val = -20*np.exp(-0.2*(0.5*((coord[0]-1)**2+(coord[1]-1)**2))**0.5)-np.exp(0.5*(np.cos(2*3.1415259*(coord[0]-1))+np.cos(2*3.1415259*(coord[1]-1))))+2.71828+20
    return val


def howMany():
    return 1


class dummySensor(module.Input):
    def __init__(self):
        module.Input.__init__(self)

        self.name = "Dummy Sensor"

        prop = []
        prop.append({"label": "Amplitude", "type": "input", "value": "0.0"})
        prop.append({"label": "Offset", "type": "input", "value": "0.0"})
        prop.append({"label": "Wait Time (s)", "type": "input", "value": "0"})
        prop.append({"label": "Function", "type": "choice", "value": 0, "choices": ["Rosenbrock", "Parabola", "Ackley"], "event": None})
        # convert dictionary to properties object
        self.parsePropertiesDict(prop)

    # this is the only additional function an input device has to have
    # returns some value
    def read(self,coord=[]):

        # wait number of seconds
        time.sleep(abs(float(self.getPropertyByLabel("wait").getValue())))
        if len(coord)==0:
          return (np.random.rand(1) - 0.5) * float(self.getPropertyByLabel("amplitude").getValue()) + float(self.getPropertyByLabel("offset").getValue())
        elif self.getPropertyByLabel("Function").getValue()==0:
          return rosenbrock_val(coord)+(np.random.rand(1) - 0.5) * float(self.getPropertyByLabel("amplitude").getValue()) + float(self.getPropertyByLabel("offset").getValue())
        elif self.getPropertyByLabel("Function").getValue()==1:
          return parabola_val(coord)+(np.random.rand(1) - 0.5) * float(self.getPropertyByLabel("amplitude").getValue()) + float(self.getPropertyByLabel("offset").getValue())
        elif self.getPropertyByLabel("Function").getValue()==2:
          return ackley_val(coord)+(np.random.rand(1) - 0.5) * float(self.getPropertyByLabel("amplitude").getValue()) + float(self.getPropertyByLabel("offset").getValue())          