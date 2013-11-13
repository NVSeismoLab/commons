#
"""
quakemlconverter.py 
 -by Mark C. Williams (2013), Nevada Seismological Laboratory

This QuakemlConverter class inherits from AntelopeEventConverter,
and generates Event objects (which then convert to QuakeML). Contains
methods to facilitate Quakeml makin' including a unique RID gen function,
and fxns to generate quakeml filename and anss attributes.

"""
from antelopeconverter import AntelopeEventConverter
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.event import (Event, CreationInfo, Magnitude,
    EventDescription, ResourceIdentifier)

from ..util import pfgetter
try:
    pf = pfgetter('db2quakeml')
except Exception:
    pf = {}
finally:
    AGENCY_CODE = pf.get('AGENCY_CODE', 'XX') 
    PLACE_DB    = pf.get('PLACE_DB', None)
    AUTH_ID     = pf.get('authority', 'local')
    EMAP        = pf.get('etypes',{})
    del pf


class QuakemlConverter(AntelopeEventConverter):
    """
    Converter that does custom site addons for NSL
    
    Methods
    -------
    build : Build up an Event using various parameters
    build(self, evid=None, orid=None, delete=False, phase_data=False, focal_data=False, mt=None):

    """
    auth_id  = AUTH_ID
    agency   = AGENCY_CODE
    place_db = PLACE_DB
    emap     = EMAP

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

    def quakeml_anss_attrib(self, evid=None):
        """
        Returns stuff necessary for quakeml files
        
        These things are specific to a datacenter, in an effort to generalize
        the actual writer function as much as possible.
        
        Input
        -----
        evid   : int of some event identifier to name the file 
        agency : str of name or code of agency creating file (netcode)
        
        Returns : dict of NSL specific stuff.
        """
        agency_code = self.agency.lower()
        if evid:
            anss_id = '{0:08d}'.format(evid)
        else:
            anss_id = '00000000'
        return {'datasource' : agency_code, 'dataid' : agency_code + anss_id, 'eventsource' : agency_code, 'eventid' : anss_id}
    
    def quakeml_filename(self, product):
        return self.event.extra['dataid']['value'] + '_' + product + '.xml'
    
    def get_nearest_event_description(self, latitude, longitude):
        nearest_city_string = self.get_nearest_city(latitude, longitude, database=self.place_db)
        return EventDescription(nearest_city_string, "nearest cities")
    
    # Use a custom RID generator function
    def _rid(self, obj):
        return self.quakeml_rid(obj, self.auth_id)

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


#--- Class as function -------------------------------------------------------
def build_event(database, *args, **kwargs):
    """
    Convenience function for NSLEventBuilder class
    See inline doc for NSLEventBuilder.build() method
    
    Inputs
    ------
    database : str or antelope.datascope.Dbptr of database
    **kwargs : keyword args to be passed to event method
    
    Returns : obspy.core.event.Event instance
    
    """
    dbc = QuakemlConverter(database)
    dbc.build(*args, **kwargs)
    dbc.connection.close()
    return dbc.event

