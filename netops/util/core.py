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
import numpy as np
import os

__antelopeversion__ = os.environ['ANTELOPE'].split(os.path.sep)[-1]

if '5.3' in __antelopeversion__:
    from netops.packets.charpacket import CharPacket as CharPkt
    from antelope.stock import pfread as pfgetter
else:
    from netops.packets.charpkt import CharPkt
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


def _timedef(comments):
    """Return timedef from a list of comments"""
    for c in comments:
        if 'timedef' in c.resource_id.resource_id:
            return c.text


def add_quality_params_from_data(origin):
    """Add OriginQuality data calculated from Origin Arrival info"""
    azimuths =  {a.azimuth for a in origin.arrivals}
    distances = {a.distance for a in origin.arrivals}
    def_azis = {a.azimuth for a in origin.arrivals if _timedef(a.comments) == 'd'}
    azi_a = np.array(list(azimuths))
    dist_a = np.array(list(distances))
    # Azimuthal gaps
    azi_a.sort()
    azi_a1 = np.roll(azi_a, -1)
    azi_a1[-1] += 360
    gaps = azi_a1 - azi_a
    # Add to quality
    if origin.quality:
        origin.quality.associated_station_count = len(dist_a)
        origin.quality.used_station_count = len(def_azis)
        origin.quality.minimum_distance = dist_a.min()
        origin.quality.maximum_distance = dist_a.max()
        origin.quality.median_distance = np.median(dist_a)
        origin.quality.azimuthal_gap = gaps.max()


def pf2json(pf):
    """Convert ParameterFile objects to json"""
    import json
    # Quick check, depricate later
    if '5.3' not in __antelopeversion__:
        return None
    return json.dumps(pf.pf2dict())

