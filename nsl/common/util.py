# -*- coding: utf-8 -*-
"""
util.py
-by Mark C. Williams, (2013) Nevada Seismological Laboratory
Utilities for the Network Operations python package

"""
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


def pnpoly(vertx, verty, testx, testy):
    """
    Check for point in polygon

    Citation
    --------
    Point inclusion in polygon test
    W. Randolph Franklin
    www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
    """
    c = False
    nvert = len(vertx)    
    j = nvert-1
    for i in range(nvert):
        if ( ((verty[i]>testy) != (verty[j]>testy)) and 
           (testx < (vertx[j]-vertx[i]) * (testy-verty[i]) / (verty[j]-verty[i]) + vertx[i]) ):
            c = not c
        j = i
    return c

