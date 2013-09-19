#!/usr/bin/env python
# 
# This is an NSL module which uses custom functions to
# make QuakeML files suitable for submission to ANSS.
#

import os
from obspy.core.event import Event, CreationInfo, Magnitude, ResourceIdentifier
from netops.converters import QuakemlConverter
from netops.converters.ichinose import mt2event

class Converter(QuakemlConverter):
    """
    Custom overrides on QuakemlConverter for NSL
    
    1) quakeml_rid : if RID is for an Event, use the web
    URL which resolves to an actual page.

    2) build : check for an 'mt' string, and run the special
    converter to get an Event/FocalMech/Mag/MomentTensor out
    of it...

    """
    @staticmethod
    def quakeml_rid(obj, authority):
        """
        Return a resource identifier for quakeml (for NSL)
        
        Inputs
        ------
        obj : str or obspy.core.event class instance
        authority : string of an auth_id, e.g. 'nn.anss.org'

        Returns
        -------
        obspy.core.event.ResourceIdentifier with 'resource_id' of:

        if obj:
        is an Event 
            => use the URL provided and tack on EVID
        is an event object (like a Pick, MomentTensor, etc)
            => id is "quakeml:<tag>/<ClassName>/<creation_info.version>
        is a string
            => append the string to "quakeml:<tag>/"
        

        NOTES: Currently, a Magnitude is a special case, if there is no
        magid, a Magnitude will get the orid as its version, which must
        be combined with the magnitude type to produce a unique id.
        
        """
        # Build up a list of strings to join for a valid RID string
        if isinstance(obj, str):
            l = ['quakeml:' + authority, obj]
        elif isinstance(obj, Event):
            evid = obj.creation_info.version
            l = ['quakeml:'+ authority, 'Events/main.php?evid=' + evid]
        else:
            prefix = 'quakeml:'+ authority
            name   = obj.__class__.__name__
            id_num = obj.creation_info.version
            l = [prefix, name, id_num]
        # In case of multiple magnitudes, make Mag unique with type
        if isinstance(obj, Magnitude):
            l.insert(2, obj.magnitude_type)
            
        ridstr = '/'.join(l)
        return ResourceIdentifier(ridstr)
    
    def build(self, evid=None, orid=None, delete=False, phase_data=False, focal_data=False, mt=None):
        """
        Build up an Event object
    
        Inputs
        ------
        evid       : int of EVID
        orid       : int of ORID
        delete     : bool of whether to mark event deleted (False)
        phase_data : bool of whether to include phase arrivals for event (False)
        focal_data : bool of whether to look for focal mechanisms (False)
        mt         : file/contents of NSL moment tensor (Ichinose)

        Returns : obspy.core.event.Event
        
        """
        #--- Build an Event based on params --------------------------------------
        if evid is None and orid:
            try:
                evid = self._evid(orid)
            except:
                pass
        # 1. Build a stub Event to send a delete
        if delete:
            self.event = Event(event_type="not existing")
            self.event.creation_info = CreationInfo(version=evid, creation_time=UTCDateTime())
            self.event.resource_id = self._rid(self.event)
        elif mt:
        # 2. Make a custom event (mt is a special-formatted text file)
            self.event = mt2event(mt, quakeml_rid=self.quakeml_rid)
        # 3. Use EventBuilder to get Event from the db
        else:
            self._build(orid=orid, phases=phase_data, focals=focal_data, event_type="not reported")
        
        # if no EVID reported, try to get it from the db (version attribute)
        if not evid:
            evid = int(self.event.creation_info.version)
        
        # Add a nearest event string, try to set event type with custom etype additions
        prefor = self.event.preferred_origin()
        if prefor is not None:
            self.event.event_type = self.origin_event_type(prefor, emap=self.emap)
            ed = self.get_nearest_event_description(prefor.latitude, prefor.longitude)
            self.event.event_descriptions = [ed]
        
        # Generate NSL namespace attributes
        extra_attributes = self.quakeml_anss_attrib(evid)
        self.event.extra = self.extra_anss(**extra_attributes)


def db2qml(**kwargs):
    """
    Function to run an Event converter and produce some
    QuakeML, returns a dict with a name and contents of
    the file as a string.

    """
    if   'delete' in kwargs and kwargs['delete']:
        product = "delete"
    elif 'mt' in kwargs and kwargs['mt'] is not None:
        product = 'moment'
    elif 'focal_data' in kwargs and kwargs['focal_data']:
        product = 'focal'
    elif 'phase_data' in kwargs and kwargs['phase_data']:
        product = "phase"
    else:
        product = "origin"
    
    database = kwargs.pop('database')
    with Converter(database) as eb:
        eb.build(**kwargs)
        qml_text = eb.quakeml_str()
        qml_file = eb.quakeml_filename(product)
    return {'name': qml_file, 'contents': qml_text}

def write_quakeml(path=None, **kwargs):
    """
    Writes QuakeML to file from a db, all keyword input args
    are passed to EventBuilder.build() function, at NSL this
    is custom, see eventbuilder.EventBuilder or the version
    netops.NSLEventBuilder's 'build' method for details.
   
    Inputs
    ------
    path : str of directory to save file in
    **kwargs
        - passed to EventBuilder.build()
        - depend on implementation
    """
    qml = db2qml(**kwargs)
    if path:
        qml_file = os.path.join(path, qml['name'])
    else:
        qml_file = qml['name']
    
    try: 
        with open(qml_file,'w') as qf:
            qf.write(qml['contents'])
    except IOError:
        qml_file = ''
    
    return [ qml_file ]

# Quickie call for x script (for testing, may go away)
#
# USAGE: ./db2qml.py <database> <orid>
#
if __name__=="__main__":
    import sys
    qml = db2qml(database=sys.argv[1], orid=sys.argv[2])
    print qml['contents']
