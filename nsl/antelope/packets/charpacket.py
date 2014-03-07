# -*- coding: utf-8 -*-
"""
charpacket.py
-by Mark C. Williams (2013) Nevada Seismological Laboratory

Character packet class used by NSL for message passing in ORBs
(Updated for new Packet class in Antelope 5.3)

"""
from antelope.Pkt import Packet
from packet_conf import (subcode_content, int_types as INT_TYPES,
                         float_types as FLOAT_TYPES)

def _entype(key, value, int_types=INT_TYPES, float_types=FLOAT_TYPES):
    """
    Convert hashed values to other types based on a lookup
    
    Notes
    -----
    Lookup lists are in module namespace
    
    """
    if value:
        if key in int_types:
            value =  int(value)
        elif key in float_types:
            value = float(value)
        else:
            value = str(value)
    return value


class CharPacket(Packet):
    """
    Packet type with helpers for NSL's character packets
    
    Highlights:
    Bare constructor pre-sets everything for a "character" packet
    Can create and break up a delimited text string

    Attributes
    ----------
    separator : string of delimiter for Pkt.string (':')

    Methods
    -------
    separate : return list of Pkt.string split on 'separator'
    unpickle : return a dict mapped to values based on subcode
    pickle   : convert an object to string and add to Pkt.string

    Constructor Methods
    -------------
    __init__    : standard constructor for Pkt type, with 'ch' pkttype
    from_object : create CharPkt instance with an object to pickle
    
    """
    separator = ':'

    def __init__(self, *args):
        """
        Create a Pkt

        If bare constructor, set pkttype, type, srcnameparts
        for a character packet (suffix='ch')
        
        Check packet is type Pkt_ch (code 7), and raise error if not
        
        Inputs
        ------
        See antelope.Pkt.Pkt constructor

        """
        if args:
            if not args[2].endswith('\x00'):
                args = list(args)
                args[2] += '\x00\x00'

        super(CharPacket, self).__init__(*args)
        
        if not args:
            self.type_suffix = 'ch'

        if self.type_suffix != 'ch':
            raise ValueError("Not a character packet! Check suffix/type...")

    def get_subcode(self):
        """
        Subcode access
        """
        return self.srcname.subcode
    
    def set_subcode(self, value):
        """
        Subcode access
        """
        self.srcname.subcode = value

    def separate(self):
        """
        Returns list of strings broken by a separator

        """
        return self.string.split(self.separator)

    def unpickle(self):
        """
        Return a dictionary of character packet content if subcode is recognized.
        Else return list split on 'separator' attribute.

        """
        if self.srcname.subcode in subcode_content:
            keys = subcode_content[self.srcname.subcode]
            if len(keys) > 1:
                values = self.separate()
            else:
                values = [self.string,]
            return dict([( key, _entype(key,values[n]) ) for n, key in enumerate(keys)])
        else:
            return self.separate()

    def _pickle(self, content, pkt_code=None):
        """
        Try to create character packet string from an object

        """
        separator = self.separator

        if isinstance(content, dict):
            if pkt_code in subcode_content:
                labels = subcode_content[pkt_code]
            else:
                labels = content.iterkeys()
            pickle = separator.join([str(content[key]) for key in labels])
        
        elif isinstance(content, list) or isinstance(content, tuple):
            pickle= separator.join(content)

        elif isinstance(content, str):
            pickle = content

        else:
            try:
                pickle = str(content)
            except Exception as e:
                raise ValueError("Couldn't convert object to a string")
        return pickle
    
    def pickle(self, obj, subcode=None):
        """
        Form a character packet string from an object

        obj     : sequence/mapping OR anything with a string method
        subcode : str subcode of packet for ordering mapping and naming packet
        
        """
        self.string = self._pickle(obj, pkt_code=subcode)
        if subcode is not None:
            self.srcname.subcode = subcode

    @classmethod
    def from_object(cls, *args, **kwargs):
        """
        Create a character packet from an object

        obj     : sequence/mapping OR anything with a string method
        subcode : str subcode of packet for ordering mapping and naming packet
        
        """
        cpkt = cls()
        cpkt.pickle(*args, **kwargs)
        return cpkt


