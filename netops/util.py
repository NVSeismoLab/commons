#
# Utilities for the netops package
#
"""
util.py
-by Mark C. Williams, (2013) Nevada Seismological Laboratory
Utilities for the Network Operations python package

This module provides:

Attributes
----------
__antelopeversion__ : version of antelope currently sourced

Classes
-------
CharPkt : Antelope version agnostic-ish NSL Character packet class

Functions
---------
pfgetter : Antelope version agnostic pf loading fucntion
aximuth2compass : get letter compass direction from a 0-360

"""
import os

__antelopeversion__ = os.environ['ANTELOPE'].split(os.path.sep)[-1]

if '5.3' in __antelopeversion__:
    from packets.charpacket import CharPacket as CharPkt
    from antelope.stock import pfread as pfgetter
else:
    from packets.charpkt import CharPkt
    from antelope.stock import pfget as pfgetter


def azimuth2compass(azimuth):
    """
    Return 1 of 8 compass directions from an azimuth in degrees from N
    
    Inputs
    ------
    azimuth : float in range (0., 360.)
    
    Returns : str of WESN compass direction
    """
    needle = None
    if azimuth < 22.5:
        needle = 'N'
    elif azimuth < 67.5:
        needle = 'NE'
    elif azimuth < 112.5:
        needle = 'E'
    elif azimuth < 157.5:
        needle = 'SE'
    elif azimuth < 202.5:
        needle = 'S'
    elif azimuth < 247.5:
        needle = 'SW'
    elif azimuth < 292.5:
        needle = 'W'
    elif azimuth < 337.5:
        needle = 'NW'
    else:
        needle = 'N'
    return needle

