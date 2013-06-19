#
# Utilities for the netops package
#
"""
This module provides:

Attributes
----------
__antelopeversion__ : version of antelope

Classes
-------
CharPkt : Character packet class (version specific)

Functions
---------
pfgetter : version agnostic pf loading fucntion

"""
import os

__antelopeversion__ = os.environ['ANTELOPE'].split(os.path.sep)[-1]

if '5.3' in __antelopeversion__:
    from charpacket import CharPacket as CharPkt
    from antelope.stock import pfread as pfgetter
else:
    from charpkt import CharPkt
    from antelope.stock import pfget as pfgetter

