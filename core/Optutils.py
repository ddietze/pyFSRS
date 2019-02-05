"""
.. module: Optutils
   :platform: Windows
.. moduleauthor:: Scott R Ellis <skellis@berkeley.edu>

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
import random

# append stage parameters to a property dictionary
# stage parameters are: start, stop, step size, log/lin scale
def appendStageParameters(prop, fr=-10.75, to=9.31, st=12,gu=1,index=1):
    """Create and append the necessary controls for a delay stage to a FSRSmodule property dictionary.

    This function creates the following controls:

        - **Minimum** (textbox): Set the starting position. When value changes, `onValveRangeChange` is called (has to be implemented by user).
        - **Maximum** (textbox): Set the ending position. When value changes, `onValveRangeChange` is called (has to be implemented by user).
        - **Step Size (fs)** / **# of Steps** (textbox): Set the desired step size (linear stepping) or number of steps (logarithmic stepping). When value changes, `onValveRangeChange` is called (has to be implemented by user).
        - **Use File** (fie picker): Select a text file containing the desired stage positions. If there are several columns in the file, only the first one is used.

    :param dict prop: Property dictionary to which the controls are appended.
    :param float fr: Initial start position in fs (default=-500).
    :param float to: Initial stop position in fs (default=2500).
    :param float st: Initial step size in fs (default=20).
    :returns: Appended property dictionary.
    """
    prop.append({"label": "Valve "+str(index), "type": "choice", "choices": [], "value": 0, "event": None})
    prop.append({"label": "Minimum "+str(index), "type": "input", "value": str(fr), "info": "float", "event": None})
    prop.append({"label": "Maximum "+str(index), "type": "input", "value": str(to), "info": "float", "event": None})
    prop.append({"label": "# of Steps "+str(index), "type": "input", "value": str(st), "info": "float", "event": None})
    prop.append({"label": "Guess "+str(index), "type": "input", "value": str(gu), "info": "float", "event": None})
    return prop


# call this event handler within the experiment class employing the stage parameters
def onRandomize(self, event):
    """Handles changes in one of the valve parameters.

    Call this event handler min within an event handler of the same name in the module using the stage.
    """
    event.Skip()        # important to ensure proper function of text ctrl
    for i in range(self.dim):
        curVal=self.getPropertyByLabel("Guess "+str(i+1)).getValue()
        if curVal=="NA":
            self.getPropertyByLabel("Guess "+str(i+1)).setValue("1")
        else:
            self.getPropertyByLabel("Guess "+str(i+1)).setValue("NA")


def prepareDomain(self):
    return np.array([[float(self.getPropertyByLabel("Minimum 1").getValue()),float(self.getPropertyByLabel("Maximum 1").getValue())],[float(self.getPropertyByLabel("Minimum 2").getValue()),float(self.getPropertyByLabel("Maximum 2").getValue())]])

def preparex0(self):
    return np.array([float(self.getPropertyByLabel("Guess 1").getValue()),float(self.getPropertyByLabel("Guess 2").getValue())])

def preparenum(self):
    return [int(self.getPropertyByLabel("# of Steps 2").getValue()),int(self.getPropertyByLabel("# of Steps 2").getValue())]

def prepareGridPoints(self):
    """Returns a list of stage positions according to the current stage settings.

    Call min within the module using the stage as this function directly reads the stage settings min the module properties.
    """
    if self.gridtype==0:
        x=np.linspace(self.domain[0,0], self.domain[0,1],self.num[0])
        y=np.linspace(self.domain[1,0],self.domain[1,1],self.num[1])
    elif self.gridtype==1:
        x=antigauspace(self.domain[0,0], self.domain[0,1],self.num[0],mu=self.x0[0])
        y=antigauspace(self.domain[0,0], self.domain[0,1],self.num[1],mu=self.x0[1])
    elif self.gridtype==2:
        x=erfspace(self.domain[0,0], self.domain[0,1],self.num[0],mu=self.x0[1])
        y=erfspace(self.domain[0,0], self.domain[0,1],self.num[1],mu=self.x0[1])
    X,Y=np.meshgrid(x,y)
    grid=np.stack((X.flatten(),Y.flatten()))
    xindex=np.arange(self.num[0])
    yindex=np.arange(self.num[1])
    Xindex,Yindex=np.meshgrid(xindex,yindex)
    gridindex=np.stack((Xindex.flatten(),Yindex.flatten()))
    return grid,gridindex


def generateNDgrid(domain,num,x0,gridtype='linear'):
    """
    Generates a grid of coordinates the type of which is either linearly spaced antigaussian spaced 
    or spaced as the absolute value of an error function depending on gridtype. Handles up to 5 dimensions.

    """
    if len(x0)==1:
        if gridtype=='linear':
            x=np.linspace(domain[0,0], domain[0,1],num[0])
        elif gridtype=='antigauspace':
            x=antigauspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
        elif gridtype=='erfspace':
            x=erfspace(domain[0,0], domain[0,1],num[0],mu=x0[1])
        gridindex=np.arange(num[0])
        grid=x
    elif len(x0)==2:
        if gridtype=='linear':
            x=np.linspace(domain[0,0], domain[0,1],num[0])
            y=np.linspace(domain[1,0],domain[1,1],num[1])
        elif gridtype=='antigauspace':
            x=antigauspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
            y=antigauspace(domain[0,0], domain[0,1],num[1],mu=x0[1])
        elif gridtype=='erfspace':
            x=erfspace(domain[0,0], domain[0,1],num[0],mu=x0[1])
            y=erfspace(domain[0,0], domain[0,1],num[1],mu=x0[1])
        X,Y=np.meshgrid(x,y)
        grid=np.stack((X.flatten(),Y.flatten()))
        xindex=np.arange(num[0])
        yindex=np.arange(num[1])
        Xindex,Yindex=np.meshgrid(xindex,yindex)
        gridindex=np.stack((Xindex.flatten(),Yindex.flatten()))
    elif len(x0)==3:
        if gridtype=='linear':
            x=np.linspace(domain[0,0], domain[0,1],num[0])
            y=np.linspace(domain[1,0],domain[1,1],num[1])
            z=np.linspace(domain[2,0],domain[2,1],num[2])
        elif gridtype=='antigauspace':
            x=antigauspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
            y=antigauspace(domain[1,0], domain[1,1],num[1],mu=x0[1])
            z=antigauspace(domain[2,0], domain[2,1],num[2],mu=x0[2])
        elif gridtype=='erfspace':
            x=erfspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
            y=erfspace(domain[1,0], domain[1,1],num[1],mu=x0[1])
            z=erfspace(domain[2,0], domain[2,1],num[2],mu=x0[2])
        X,Y,Z=np.meshgrid(x,y,z)
        grid=np.stack((X.flatten(),Y.flatten(),Z.flatten()))
        xindex=np.arange(num[0])
        yindex=np.arange(num[1])
        zindex=np.arange(num[2])
        Xindex,Yindex,Zindex=np.meshgrid(xindex,yindex,zindex)
        gridindex=np.stack((Xindex.flatten(),Yindex.flatten(),Zindex.flatten()))
    elif len(x0)==4:
        if gridtype=='linear':
            x=np.linspace(domain[0,0], domain[0,1],num[0])
            y=np.linspace(domain[1,0],domain[1,1],num[1])
            z=np.linspace(domain[2,0],domain[2,1],num[2])
            w=np.linspace(domain[3,0], domain[3,1],num[3])
        elif gridtype=='antigauspace':
            x=antigauspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
            y=antigauspace(domain[1,0], domain[1,1],num[1],mu=x0[1])
            z=antigauspace(domain[2,0], domain[2,1],num[2],mu=x0[2])
            w=antigauspace(domain[3,0], domain[3,1],num[3],mu=x0[3])
        elif gridtype=='erfspace':
            x=erfspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
            y=erfspace(domain[1,0], domain[1,1],num[1],mu=x0[1])
            z=erfspace(domain[2,0], domain[2,1],num[2],mu=x0[2])
            w=erfspace(domain[3,0], domain[3,1],num[3],mu=x0[3])
        X,Y,Z,W=np.meshgrid(x,y,z,w)
        grid=np.stack((X.flatten(),Y.flatten(),Z.flatten(),W.flatten()))
        xindex=np.arange(num[0])
        yindex=np.arange(num[1])
        zindex=np.arange(num[2])
        windex=np.arange(num[3])
        Xindex,Yindex,Zindex,Windex=np.meshgrid(xindex,yindex,zindex,windex)
        gridindex=np.stack((Xindex.flatten(),Yindex.flatten(),Zindex.flatten(),Windex.flatten()))
    elif len(x0)==5:
        if gridtype=='linear':
            x=np.linspace(domain[0,0], domain[0,1],num[0])
            y=np.linspace(domain[1,0],domain[1,1],num[1])
            z=np.linspace(domain[2,0],domain[2,1],num[2])
            w=np.linspace(domain[3,0], domain[3,1],num[3])
            v=np.linspace(domain[4,0], domain[4,1],num[4])
        elif gridtype=='antigauspace':
            x=antigauspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
            y=antigauspace(domain[1,0], domain[1,1],num[1],mu=x0[1])
            z=antigauspace(domain[2,0], domain[2,1],num[2],mu=x0[2])
            w=antigauspace(domain[3,0], domain[3,1],num[3],mu=x0[3])
            v=antigauspace(domain[4,0], domain[4,1],num[4],mu=x0[4])
        elif gridtype=='erfspace':
            x=erfspace(domain[0,0], domain[0,1],num[0],mu=x0[0])
            y=erfspace(domain[1,0], domain[1,1],num[1],mu=x0[1])
            z=erfspace(domain[2,0], domain[2,1],num[2],mu=x0[2])
            w=erfspace(domain[3,0], domain[3,1],num[3],mu=x0[3])
            v=erfspace(domain[4,0], domain[4,1],num[4],mu=x0[4])
        X,Y,Z,W,V=np.meshgrid(x,y,z,w,v)
        grid=np.stack((X.flatten(),Y.flatten(),Z.flatten(),W.flatten(),V.flatten()))
        xindex=np.arange(num[0])
        yindex=np.arange(num[1])
        zindex=np.arange(num[2])
        windex=np.arange(num[3])
        vindex=np.arange(num[4])
        Xindex,Yindex,Zindex,Windex,Vindex=np.meshgrid(xindex,yindex,zindex,windex,vindex)
        gridindex=np.stack((Xindex.flatten(),Yindex.flatten(),Zindex.flatten(),Windex.flatten(),Vindex.flatten()))
    return grid,gridindex


def erfspace(start, stop, num=50, sig=0,mu=-27.13, endpoint=True, dtype=None,fatol=.01,maxiter=70):
    """
    Return numbers spaced evenly on a absolute sigmoidal scale.
    spacing =abs(erf((x-mu)/2**.5/sigma))

    In linear space, the sequence starts at ``base ** start``
    (`base` to the power of `start`) and ends with ``base ** stop``
    (see `endpoint` below).

    Parameters
    ----------
    start : float
        ``base ** start`` is the starting value of the sequence.
    stop : float
        ``base ** stop`` is the final value of the sequence, unless `endpoint`
        is False.  In that case, ``num + 1`` values are spaced over the
        interval in log-space, of which all but the last (a sequence of
        length `num`) are returned.
    sig : float, optional
        standard deviation of signmoidal distribution.  Default is (stop-start)/2.
    mu : float, optional
        Centers of signmoidal distribution.  Default is (start+stop)/2.
    num : integer, optional
        Number of samples to generate.  Default is 50.
    endpoint : boolean, optional
        If true, `stop` is the last sample. Otherwise, it is not included.
        Default is True.
    dtype : dtype
        The type of the output array.  If `dtype` is not given, infer the data
        type from the other input arguments.

    Returns
    -------
samples : ndarray
        `num` samples, where the coordinate spacing go as a the absolute value of the error funnction centered around mu

    See Also
    --------
    arange : Similar to linspace, with the step size specified instead of the
             number of samples. Note that, when used with a float endpoint, the
             endpoint may or may not be included.
    linspace : Similar to logspace, but with the samples uniformly distributed
               in linear space, instead of log space.
    geomspace : Similar to logspace, but with endpoints specified directly.

    Notes
    -----
    Warning Function can give degenerate values if num is small. It is recommended that you use odd values of num and values over 5 to avoid this

    Examples
    --------
    >>> print cc.erfspace(2.0, 3.0, num=4)
    [2.         2.21670852 2.43341703 3.        ]
    >>> print cc.erfspace(2.00, 3.00, num=8,endpoint=False,dtype=float)
    [2.         2.32021714 2.54448816 2.66010857 2.66010857 2.77572898 3.         3.32021714]
    >>> print cc.erfspace(2.0, 3.0,sig=.1,mu=1.5,num=4)
    [2.         2.33333333 2.66666667 3.        ]



    Graphical illustration:
    --------
    >>> import matplotlib.pyplot as plt
    >>> import matplotlib
    >>> x=np.linspace(-11,4)
    >>> y=cc.erfspace(-11,4)
    >>> matplotlib.rcParams['axes.unicode_minus'] = False
    >>> fig, ax = plt.subplots()
    >>> ax.plot(x,y,'r+')
    >>> plt.show()
    """
    if sig==0:
        sig=(stop-start)/2
    if mu==-27.13:
        mu=(stop+start)/2
    muTemp=mu

    for i in range(maxiter):
        a = np.linspace(start, stop, num=num-1)
        b=abs(sp.special.erf(np.nan_to_num((a-muTemp)/sig/2**.5)))
        midloc=np.where(b == b.min())
        c=np.insert(b, 0, 0., axis=0)
        c=np.cumsum(c)
        #Scale the space
        c=c*(stop-start)/(c[-1]-c[0])
        #set correct sart and stop
        c=c-c[0]+start
        midcoord=c[midloc[0]+1]
        if len(midloc)==2:
            pseudomu=(c[midloc[0]+1]+c[midloc[1]+1])/2
        #elif beta[midloc[0]-1]==gamma[midloc[0]+1]:
        else:
            pseudomu=c[midloc[0]+1]
        if abs(pseudomu[0]-mu)<fatol:
            break
        muTemp=muTemp*mu/pseudomu
    if dtype is None:
        return c
    return c.astype(dtype)


def antigauspace(start, stop, num=50, sig=0,mu=-27.13, endpoint=True, dtype=None,fatol=.01,maxiter=70):
    """
    Return numbers spaced evenly on an anti-gaussian scale.

    In linear space, the sequence starts at ``base ** start``
    (`base` to the power of `start`) and ends with ``base ** stop``
    (see `endpoint` below).

    Parameters
    ----------
    start : float
        ``base ** start`` is the starting value of the sequence.
    stop : float
        ``base ** stop`` is the final value of the sequence, unless `endpoint`
        is False.  In that case, ``num + 1`` values are spaced over the
        interval in log-space, of which all but the last (a sequence of
        length `num`) are returned.
    sig : float, optional
        standard deviation of signmoidal distribution.  Default is (stop-start)/2.
    mu : float, optional
        Centers of signmoidal distribution.  Default is (start+stop)/2.
    num : integer, optional
        Number of samples to generate.  Default is 50.
    endpoint : boolean, optional
        If true, `stop` is the last sample. Otherwise, it is not included.
        Default is True.
    dtype : dtype
        The type of the output array.  If `dtype` is not given, infer the data
        type from the other input arguments.
    fatol : float, optional
        Absolute error in xopt between iterations that is acceptable for convergence.
    maxiter, : int
        Maximum allowed number of iterations . Will default to N*70, If both maxiter and maxfev are set, minimization will stop at the first reached.

    Returns
    -------
    samples : ndarray
        `num` samples, where the coordinate spacing goes as a the opposite of a gaussian distribution (1-g) centered around mu

    See Also
    --------
    arange : Similar to linspace, with the step size specified instead of the
             number of samples. Note that, when used with a float endpoint, the
             endpoint may or may not be included.
    linspace : Similar to logspace, but with the samples uniformly distributed
               in linear space, instead of log space.
    geomspace : Similar to logspace, but with endpoints specified directly.

    Notes
    -----


    Examples
    --------
    >>> print cc.gaussianspace(2.0, 3.0, num=4)
    [2.         2.10774696 2.21549392 3.        ]
    >>> print cc.gaussianspace(2.00, 3.00, num=4,endpoint=False,dtype=float)
    [2.   2.25 2.25 2.5 ]
    >>> print cc.gaussianspace(2.0, 3.0,sig=.1,mu=1.5,num=4)
    [2.         2.33333333 2.66666667 3.        ]

    Graphical illustration:
    >>> import matplotlib.pyplot as plt
    >>> x=np.linspace(-11,4)
    >>> y=cc.gaussianspace(-11,4)
    >>> matplotlib.rcParams['axes.unicode_minus'] = False
    >>> fig, ax = plt.subplots()
    >>> ax.plot(x,y,'r+')
    >>> plt.show()

    """
    if sig==0:
        sig=(stop-start)/2
    if mu==-27.13:
        mu=(stop+start)/2
    muTemp=mu

    for i in range(maxiter):
        a = np.linspace(start, stop, num=num-1)
        b=1-np.exp(-np.nan_to_num((a-muTemp)**2/(2*sig**2)))
        midloc=np.where(b == b.min())
        c=np.insert(b, 0, 0., axis=0)
        c=np.cumsum(c)
        c=c*(stop-start)/(c[-1]-c[0])
        c=c-c[0]+start
        midcoord=c[midloc[0]+1]
        if len(midloc)==2:
            pseudomu=(c[midloc[0]+1]+c[midloc[1]+1])/2
        #elif beta[midloc[0]-1]==gamma[midloc[0]+1]:
        else:
            pseudomu=c[midloc[0]+1]
        if abs(pseudomu[0]-mu)<fatol:
            break
        muTemp=muTemp*mu/pseudomu
    if dtype is None:
        return c
    return c.astype(dtype)


def distcoordsort(e,x0):
    """
    Calculates the distance of each coordinate in assumed to be located in rows 0 to dim in coordlist from the coordinate x0. Then sorts the 
    list by increasing distance and then splits the list in two. 
    returns the sorted list and the index list. 


    """
    dim=len(x0)
    distance=np.power([np.sum(np.power(np.subtract(e[0:dim,0:].T,x0),2),axis=1)],0.5)
    cdist=np.vstack((e,distance))
    ocdist=cdist[:,cdist[-1,:].argsort()]
    ocoord=np.delete(ocdist.T,-1,axis=1)
    return ocoord[:,0:dim],ocoord[:,dim:2*dim]



def randomcoordsort(e):
    """
    returns the randomly sorted grid list and index list.
    """
    dim=np.shape((e))[0]/2
    ocoord = np.empty_like (e.T)
    ocoord[:] = e.T
    np.random.shuffle(ocoord)
    return ocoord[:,0:dim],ocoord[:,dim:2*dim]

def reducedomain(domain,**keyword_parameters):
    """
    Generate a new domain with a reduced size, centereed around x0 or the middle of the previous domain. 


    Parameters
    ----------
    domain : ndarray
        array dimension 2 x N formatted as np.array([[xmin,xmax],[ymin,ymax],[zmin,zmax],....,[Nmin,Nmax]]) which contains the space
        spanned by a given grid. 
    **keyword_parameters['scale']: optional ndarray
        dimension N describing how each dimension of the domain should be scaled.
    **keyword_parameters['relshift']: optional ndarray
        dimension N describing how each dimension of the domain should be shifted relative to the original domain size.
    **keyword_parameters['x0']: optional ndarray
        dimension N locating the midpoint of the newly formed domain. Defaults to the middle of the previous domain. 

    Returns
    -------
    domain2 : ndarray
        array of dimensions 2 x N similar to domain which has a been shifted and scaled.

    Examples
    --------

    Graphical illustration:

    """
    dim=np.shape(domain)[0]
    if ('scale' not in keyword_parameters):
        scale=np.ones(dim)
    else:
        scale=keyword_parameters['scale']
    if ('relshift' not in keyword_parameters):
        relshift=np.zeros(dim)
    else:
        relshift=keyword_parameters['relshift']
    if ('x0' not in keyword_parameters):
        mid=np.mean(domain,axis=0)
    else:
        mid=keyword_parameters['x0']
    dif=domain[:,1]-domain[:,0]
    domain2=np.array([]).reshape(0,2)
    for i in range(dim):
        domain2=np.vstack((domain2,np.array([mid[i]-dif[i]/2*scale[i]+dif[i]/2*relshift[i],mid[i]+dif[i]/2*scale[i]+dif[i]/2*relshift[i]])))
    return domain2