# -*- coding: utf-8 -*-
"""
Unified interface for Antelope packet

At least 'stuff' and 'unstuff' should be accessible.
"""

# Packets are non-back compatible in Antelope
#
# for now, at least make the name the same, some functions are
# different as well, need an NSL API for this, too? FML.
try:
    from antelope.Pkt import Packet as Pkt
except ImportError:
    from antelope.Pkt import Pkt

