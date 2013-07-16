#
# Custom site fuctions for the Nevada Seismological Laboratory
#
from numpy import array
import psycods2 as dbapi2
import util
from csseventconverter import CSSEventConverter
from mt import mt2event
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.util import gps2DistAzimuth
from obspy.core.event import (Catalog, Event, Origin, CreationInfo, Magnitude,
    EventDescription, OriginUncertainty, OriginQuality, CompositeTime,
    ConfidenceEllipsoid, StationMagnitude, Comment, WaveformStreamID, Pick,
    QuantityError, Arrival, FocalMechanism, MomentTensor, NodalPlanes,
    PrincipalAxes, Axis, NodalPlane, SourceTimeFunction, Tensor, DataUsed,
    ResourceIdentifier, StationMagnitudeContribution)

try:
    pf = util.pfgetter('rt_quakeml')
except Exception:
    pf = {}
finally:
    AGENCY_CODE = pf.get('AGENCY_CODE', 'XX') 
    PLACE_DB    = pf.get('PLACE_DB', None)
    AUTH_ID     = pf.get('authority', 'local')
    EMAP        = pf.get('etypes',{})


### Utility functions ########################################################
# May be moved to a more generic module in the future (+remove numpy depend)
def get_nearest_city(latitude, longitude, database=PLACE_DB):
    """
    Get the nearest place to a lat/lon from a db with a 'places' table

    Inputs
    ------
    database  : str of database with 'places' table
    latitude  : float of latitude
    longitude : float of longitude
    
    Returns : string of the distance and compass azimuth to a place

    """
    if database is None:
        return None
    else:
        dbc = dbapi2.Connection(database)
        curs = dbc.cursor(table='places', row_factory=dbapi2.NamedTupleRow)
        stats = array([gps2DistAzimuth(latitude, longitude, r.lat, r.lon) for r in curs])
        ind = stats.argmin(0)[0]
        minstats = stats[ind]
        curs.scroll(int(ind), 'absolute')
        minrec = curs.fetchone()
        dist, azi, backazi = minstats
        compass = util.azimuth2compass(backazi)
        place_info = {'distance': dist/1000., 'direction': compass, 'city': minrec.place, 'state': minrec.state}
        dbc.close()
        return  "{distance:0.1f} km {direction} of {city}, {state}".format(**place_info)


class CustomConverter(CSSEventConverter):
    """
    EventBuilder that does custom addons for NSL
    
    Methods
    -------
    build : Build up an Event using various parameters
    build(self, evid=None, orid=None, delete=False, phase_data=False, focal_data=False, mt=None):

    """
    auth_id = AUTH_ID
    agency = AGENCY_CODE

    @staticmethod
    def quakeml_rid(obj, authority):
        """
        Return a resource identifier for quakeml (for NSL)
        
        *** BASED ON NSL QuakeML CONVENTIONS! ***
            - The creation_info.version attribute holds a unique number
            - Only an Event holds the public site URL

        Inputs
        ------
        obj : str or obspy.core.event class instance
        url : Identifier to point toward an event
        tag : Site-specific tag to ID data center

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

   
    @staticmethod
    def quakeml_anss_attrib(evid=None, agency_code=None):
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
        if evid:
            anss_id = '{0:08d}'.format(evid)
        else:
            anss_id = '00000000'
        return {'datasource' : agency_code, 'dataid' : anss_id, 'eventsource' : agency_code, 'eventid' : anss_id}
    
    def quakeml_filename(self, product):
        return self.event.extra['eventsource']['value'] + self.event.extra['eventid']['value'] + '_' + product + '.xml'
    
    def get_nearest_event_description(self, latitude, longitude):
        nearest_city_string = get_nearest_city(latitude, longitude)
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
            e_type = "not existing"
            self.event = Event(event_type=e_type)
            self.event.creation_info = CreationInfo(version=evid, creation_time=UTCDateTime())
            self.event.resource_id = self._rid(self.event)
        else:
        # 2. Make a custom event (mt is a special-formatted text file)
            if mt:
                self.event = mt2event(mt)
        # 3. Use EventBuilder to get Event from the db
            else:
                self._build(orid=orid, phases=phase_data, focals=focal_data, event_type="not reported")
            # if no EVID reported, try to get it from the db (version attribute)
            if not evid:
                evid = int(self.event.creation_info.version)
        # Add a nearest event string, try to set event type with custom etype additions
        prefor = self.event.preferred_origin()
        if prefor is not None:
            self.event.event_type = self.origin_event_type(prefor, emap=EMAP)
            ed = self.get_nearest_event_description(prefor.latitude, prefor.longitude)
            self.event.event_descriptions = [ed]
        # Generate NSL namespace attributes
        extra_attributes = self.quakeml_anss_attrib(evid, AGENCY_CODE.lower())
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
    dbc = CustomConverter(database)
    dbc.build(*args, **kwargs)
    dbc.close()
    return dbc.event

