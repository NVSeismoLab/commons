#
# Utilities for the netops package
#
"""
util.py
-by Mark C. Williams, (2013) Nevada Seismological Laboratory
Utilities for the Network Operations python package

"""
import os
import numpy as np


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

