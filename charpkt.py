#
# Utilities for making character packets for our status ORBS
#

from antelope.Pkt import Pkt, suffix2pkttype, Pkt_ch
#
# Ever-growing list of subcodes and the junk in them.
#
subcode_content = {
    'event_new'          : ('evid','orid','mag','time','srcdb','snapdb'),
    'event_pre'          : ('evid','orid','mag','time','srcdb','snapdb'),
    'event_delete'       : ('evid','orid'),
    'event_old'          : ('evid','orid','mag','time','srcdb','snapdb'),
    'event_hypo'         : ('evid','orid','mag','time','srcdb','snapdb'),
    'event_mark_reviewed'   : (None,),
    'db2shakemap_pre'       : (None,),
    'rttimer_sync'          : ('interval',),
    'rtweb_delete'          : (None,),
    'rtweb_new'             : (None,),
    'rtweb_new-external'    : (None,),
    'rtweb_pre'             : (None,),
    'rtweb_pre-external'    : (None,),
    'rtweb_sync'            : ('time',),
    'reporter_hypo'         : (None,),
    'reporter_hypo-external': (None,),
    'reporter_new'          : (None,),
    'reporter_new-external' : (None,),
    'reporter_pre'          : (None,),
    'reporter_pre-external' : (None,),
    'reporter_delete'       : ('evid','orid'),
    'rt_hazus_pre'          : (None,),
    'rtfocalmech_pre'       : (None,),
    'mw_new'                : (None,),
    'mw_pre'                : (None,),
    'mw_publish'            : ('mt',),
}

# Map these to non-string types when unpickling to a dict
#
int_types   = ('evid','orid','interval')
float_types = ('mag', 'time')

def _entype(key, value):
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


class CharPkt(Pkt):
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
        super(CharPkt, self).__init__(*args)
        
        if not args:
            self.pkttype = suffix2pkttype('ch')
            self.srcnameparts['suffix'] = self.pkttype['suffix']
            self.type = self.pkttype['content']
        
        # Weird bug, dfile gets set to None when init from a packet
        # This breaks 'stuff()', so set it back to empty string.
        #
        if self.dfile is None:
            self.dfile = ''

        if self.type != Pkt_ch:
            raise ValueError("Not a character packet! Check suffix/type...")
    
    def get_subcode(self):
        """
        Subcode access

        """
        return self.srcnameparts['subcode']

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
        if self.srcnameparts['subcode'] in subcode_content:
            keys = subcode_content[self.srcnameparts['subcode']]
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
            self.srcnameparts['subcode'] = subcode

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


