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

"""
import os

__antelopeversion__ = os.environ.get('ANTELOPE', os.sep).split(os.sep)[-1]

if '5.3' in __antelopeversion__:
    from netops.packets.charpacket import CharPacket as CharPkt
    from antelope.stock import pfread as pfgetter
elif __antelopeversion__:
    from netops.packets.charpkt import CharPkt
    from antelope.stock import pfget as pfgetter
else:
    CharPkt = tuple
    pfgetter = open


def pf2json(pf):
    """Convert ParameterFile objects to json"""
    import json
    # Quick check, depricate later
    if '5.3' not in __antelopeversion__:
        return None
    return json.dumps(pf.pf2dict())

