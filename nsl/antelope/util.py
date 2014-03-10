
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

