# -*- coding: utf-8 -*-
"""
Packet classes for Antelope
nsl.antelope.packets

Classes
=======
Pkt (Standard Pkt or Packet)
CharPkt (NSL CharPkt or CharPacket)

"""
from nsl.antelope.packets.pkt import Pkt
from nsl.antelope.util import __antelopeversion__

if '5.3' in __antelopeversion__:
    from nsl.antelope.packets.charpacket import CharPacket as CharPkt
elif '5.' in __antelopeversion__:
    from nsl.antelope.packets.charpkt import CharPkt
else:
    raise ImportError("Can't import Character packet for Vers: {0}".format(
                       __antelopeversion__)
