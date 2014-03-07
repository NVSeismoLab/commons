
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

"""
import os

__antelopeversion__ = os.environ.get('ANTELOPE', os.sep).split(os.sep)[-1]




#-------------------------------------------------------#
# DEPRICATED, here for one version for backwards compat #
#-------------------------------------------------------#
if '5.3' in __antelopeversion__:
    from netops.packets.charpacket import CharPacket as CharPkt
    from antelope.stock import pfread as pfgetter
elif __antelopeversion__:
    from netops.packets.charpkt import CharPkt
    from antelope.stock import pfget as pfgetter
else:
    CharPkt = tuple
    pfgetter = open
#-------------------------------------------------------#

