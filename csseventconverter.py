#
# csseventconverter.py 
# by Mark
# 2013-2-13
#
# functions to map Antelope css3.0 to obspy Event class
# which can then write out QuakeML
#
# Required     'obspy'    ObsPy (version with event, quakeml support)
# Packages     'psycods2' DBAPI2.0 implementation for Datascope
#
import psycods2 as dbapi2
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.event import (Catalog, Event, Origin, CreationInfo, Magnitude,
    EventDescription, OriginUncertainty, OriginQuality, CompositeTime,
    ConfidenceEllipsoid, StationMagnitude, Comment, WaveformStreamID, Pick,
    QuantityError, Arrival, FocalMechanism, MomentTensor, NodalPlanes,
    PrincipalAxes, Axis, NodalPlane, SourceTimeFunction, Tensor, DataUsed,
    ResourceIdentifier, StationMagnitudeContribution)

AUTH_ID = 'local'

try:
    from util import pfgetter
    pf = pfget('site')
except Exception:
    pf = {}
finally:
    AGENCY_CODE = pf.get('default_seed_network','xx').upper()


def default_rid(obj, authority=AUTH_ID):
    """
    Return generic unique ResourceID
    
    With no pf or custom function available, will produce a 
    ResourceIdentifier exactly like the ObsPy default for a
    QuakeML file.

    """
    return ResourceIdentifier(prefix='smi:'+ authority)


class CSSEventConverter(dbapi2.Connection):
    """
    Connection to build an ObsPy Event instance from CSS3.0 database
    (Antelope only, for now).

    This class inherits from a DBAPI 2.0-compat Connection for Datascope.
    
    Attributes
    ----------
    auth_id : str of authority URL (publicID)
    agency  : str of short agency identifier (net code)
    event   : obspy.core.event.Event current instance (blank Event)
    catalog : obspy.core.event.Catalog containing current Event 

    Methods
    -------
    get_origins    : return list of Origins from db
    get_magnitudes : return list of Magnitudes from db
    get_phases     : return lists of Pick/Arrivals from db
    get_focalmechs : return list of FocalMechanisms from db
    build          : build an Event given some parameters (ORID)
    quakeml_str    : write the current Event out as QuakeML
    extra_anss     : return properly formatted 'extra' dict for ANSS QuakeML
    get_event_type : static class method to convert CSS origin type flag

    Notes
    -----
    The four main 'get' methods (origin, mag, focalmech, and phases) contain
    the esoteric database calls. All other methods use standard Python 
    iterators, generators, and dict-like key access to fields, and are 
    abstracted through the DBAPI standard interface. This should make the
    schema translator functions fairly portable. To that end...
    
    Future implementations of this class will most likely work with additional
    database backends, and only depend on the standardish CSS3.0 schema.

    """
    event   = None
    auth_id = AUTH_ID
    agency  = AGENCY_CODE

    def __init__(self, *args, **kwargs):
        """
        Open a database connection and initialize Event for extracting info.

        The constructor for CSSEventConverter is identical to that of its 
        parent dbapi2.Connection for now, with the addition of:
        
         - setting the 'event' attribute to a blank obspy.core.event.Event.
         - explictly using the OrderedDictRow row_factory, for dict access
            to the Cursor database fields.

        Inputs
        ------
        database : str of database name
        perm     : str of database permission ('r')

        Notes
        -----
        In future, could also set an existing Event to append to.
        For now, simply do this after construction.
        
        >>> eb = CSSEventConverter(my_db, perm='r')
        >>> eb.event = my_event

        """
        super(self.__class__, self).__init__(*args, **kwargs)
        self.row_factory = dbapi2.OrderedDictRow
        self.event = Event()
    
    @staticmethod 
    def get_event_type(etype, emap_update=None):
        """
        Map a CSS3.0 etype origin flag to a QuakeML event type
        
        Default dictionary will be updated by anything in 'emap_update'

        Inputs
        ------
        etype : str of a valid etype
        emap_update : add/replace mappings to the standard css3.0 one

        """
        event_type_map = {
            'qb' : "quarry blast",
            'eq' : "earthquake",
            'me' : "meteorite",
            'ex' : "explosion",
            'o'  : "other event",
            'l'  : "earthquake",
            'r'  : "earthquake",
            't'  : "earthquake",
            'f'  : "earthquake",
        }
        # Add custom flags
        if emap_update:
            event_type_map.update(emap_update)
        # Try to find a direct match, then check for stuff like 'LF'
        if etype.lower() in event_type_map:
            return event_type_map[etype.lower()]
        else:
            for k,v in event_type_map.iteritems():
                if k in etype.lower():
                    return v
    
    @classmethod
    def origin_event_type(cls, origin, emap=None):
        """Return a proper event_type from a CSS3.0 etype flag stored in an origin Comment"""
        if origin.comments:
            for comm in origin.comments:
                if 'etype' in comm.resource_id.resource_id:
                    etype = comm.text
                    return cls.get_event_type(etype, emap_update=emap)
    
    @staticmethod
    def extra_anss(**kwargs):
        """
        Create an dictionary for ANSS vars for use by event classes 'extra' attribute
        
        Inputs
        ------
        kwargs SHOULD be one of ('datasource','dataid','eventsource','eventid')
        
        Returns : dict of obspy 'extra' format

        """
        extra_attrib = {} 
        ns_anss = ['catalog', 'http://anss.org/xmlns/catalog/0.1'] 
        for a in kwargs:
            extra_attrib[a] = {'value': kwargs[a],  '_namespace': ns_anss, '_type': 'attribute'}
        return extra_attrib
    
    @staticmethod
    def _rid(obj):
        return default_rid(obj)    
    
    @staticmethod
    def _create_dict(dbtuple, field):
        """
        Make a dict of {field:value} only if field is not NULL
        
        Inputs
        ------
        dbtuple : dict containing value to use
        field   : str of valid field name in dbtuple

        Returns : dict of {field:value}

        """
        value = dbtuple.get(field)
        if value:
            return { field : value }
        else:
            return None
    
    def _evid(self, orid):
        """
        Return EVID from a known ORID
        
        Inputs
        ------
        int of orid

        Returns : int of evid

        """
        curs = self.cursor(table='origin')
        n = curs.execute('find', ['orid=={0}'.format(orid)] )
        curs.scroll(n, 'absolute')
        db = curs.fetchone()
        return db['evid']

    def _map_join2origin(self, db):
        """
        Returns an Origin instance from a Dbtuple
        
        Inputs
        ------
        db :  dict of an origin-origerr joined record

        Returns : obspy.core.event.Origin

        """ 
        # majax plunge, rotation are Tait-Bryan angles phi, theta
        ellipse = ConfidenceEllipsoid(
            major_axis_plunge = 0, 
            major_axis_rotation = 0,
            semi_minor_axis_length        = db.get('sminax'),
            semi_major_axis_length        = db.get('smajax'),
            semi_intermediate_axis_length = db.get('sdepth'),
            major_axis_azimuth            = db.get('strike'),
            )
        
        quality = OriginQuality(
            associated_phase_count = db.get('nass'),
            used_phase_count       = db.get('ndef'),
            standard_error         = db.get('sdobs'),
            )

        origin               = Origin()
        origin.latitude      = db.get('lat')
        origin.longitude     = db.get('lon')
        origin.depth         = db.get('depth')
        origin.time          = UTCDateTime(db['time'])
        origin.quality       = quality
        origin.creation_info = CreationInfo(
            creation_time = UTCDateTime(db['lddate']),
            agency_id     = self.agency, 
            version       = str(db['orid']),
            )

        origin.origin_uncertainty = OriginUncertainty(
            confidence_ellipsoid  = ellipse,
            preferred_description = "confidence ellipsoid",
            ) 
        
        if db.get('conf') is not None:
            origin.origin_uncertainty.confidence_level = db.get('conf') * 100.

        if 'orbassoc' in db['auth']:
            origin.evaluation_mode   = "automatic"
            origin.evaluation_status = "preliminary"
        else:
            origin.evaluation_mode   = "manual"
            origin.evaluation_status = "reviewed"
        # Save etype in a comment due to schema differences...
        etype_comment = Comment(resource_id=ResourceIdentifier("smi:"+self.auth_id+"/comment/etype/"+str(db['orid'])), text=db['etype'])
        origin.comments = [etype_comment]
        origin.resource_id = self._rid(origin)
        return origin
    
    def _map_netmag2magnitude(self, db):
        """Get Magnitude from Dbtuple of a netmag record"""
        m = Magnitude()
        m.mag             = db.get('magnitude')
        m.magnitude_type  = db.get('magtype')
        m.station_count   = db.get('nsta')
        m.creation_info   = CreationInfo(
            creation_time = UTCDateTime(db['lddate']),
            agency_id     = self.agency,
            version       = db.get('magid'),
            author        = db.get('auth'),
            )
        if m.creation_info.author.startswith('orb'):
            m.evaluation_status = "preliminary"
        else:
            m.evaluation_status = "reviewed"
        m.resource_id = self._rid(m)
        return m

    def _map_origin2magnitude(self, db, mtype='ml'):
        """Get Magnitude from Dbtuple of an origin record"""
        m = Magnitude()
        m.mag             = db.get(mtype)
        m.magnitude_type  = mtype 
        m.creation_info   = CreationInfo(
            creation_time = UTCDateTime(db['lddate']), 
            agency_id     = self.agency,
            version       = db.get('orid'),
        	author        = db['auth'],
            )
        if m.creation_info.author.startswith('orb'):
            m.evaluation_status = "preliminary"
        else:
            m.evaluation_status = "reviewed"
        m.resource_id = self._rid(m)
        return m


    def _map_join2phase(self, db):
        """
        Return an obspy Arrival and Pick from a Dbtuple
        of records in an assoc-arrival join
        
        Inputs
        ------
        db : dict of database record

        Returns : pick, arrival
        -------
            obspy.core.event.Pick
            obspy.core.event.Arrival

        """
        p = Pick()
        p.time = UTCDateTime(db['time'])
        p.waveform_id = WaveformStreamID(station_code = db.get('sta'), 
                                         channel_code = db.get('chan'),
                                         network_code = db.get('net'),
                                         )
        p.horizontal_slowness = db.get('slow')
        p.horizontal_slowness_errors = self._create_dict(db, 'delslo')
        p.backazimuth = db.get('azimuth')
        p.backazimuth_errors = self._create_dict(db, 'delaz')
        
        on_qual = db['qual'].lower()
        if 'i' in on_qual:
            p.onset = "impulsive"
        elif 'e' in on_qual:
            p.onset = "emergent"
        elif 'w' in on_qual:
            p.onset = "questionable"
        else:
            p.onset =  None
        
        p.phase_hint = db.get('iphase')
        
        pol = db['fm'].lower()
        if 'c' in pol or 'u' in pol:
            p.polarity = "positive"
        elif 'd' in pol or 'r' in pol:
            p.polarity = "negative"
        elif '.' in pol:
            p.polarity = "undecidable"
        else:
            p.polarity = None
        
        p.evaluation_mode = "automatic"
        if 'orbassoc' not in db['auth']:
            p.evaluation_mode = "manual"
        
        p.evaluation_status = "preliminary"
        if p.evaluation_mode is "manual":
            p.evaluation_status = "reviewed"
        
        p.creation_info = CreationInfo(
            version = db['arid'], 
            creation_time = UTCDateTime(db['arrival.lddate']), 
            agency_id = self.agency, 
            author = db.get('auth'),
            )

        p.resource_id = self._rid(p)

        # Now do the arrival
        a = Arrival()
        a.pick_id = ResourceIdentifier(p.resource_id.resource_id, referred_object=p)
        a.phase = db.get('phase')
        a.azimuth = db.get('esaz')
        a.distance = db.get('delta')
        a.takeoff_angle = db.get('ema')
        a.takeoff_angle_errors = self._create_dict(db, 'emares')
        a.time_residual = db.get('timeres')
        a.horizontal_slowness_residual = db.get('slores')
        a.time_weight = db.get('wgt')
        a.earth_model_id = ResourceIdentifier('smi:'+self.auth_id+'/VelocityModel/'+db['vmodel'])
        a.creation_info = CreationInfo(
            version = db['arid'], 
            creation_time = UTCDateTime(db['lddate']),
            agency_id = self.agency,
            )
        a.resource_id = self._rid(a)
        return p, a

    def _map_fplane2focalmech(self, db):
        fm = FocalMechanism()
        
        nps = NodalPlanes()
        #nps.nodal_plane_1 = NodalPlane(db.get('str1'), db.get('dip1'), db.get('rake1'))
        #nps.nodal_plane_2 = NodalPlane(db.get('str2'), db.get('dip2'), db.get('rake2'))
        nps.nodal_plane_1 = NodalPlane(db['str1'], db['dip1'], db['rake1'])
        nps.nodal_plane_2 = NodalPlane(db['str2'], db['dip2'], db['rake2'])
        
        nps.preferred_plane = 1
        
        prin_ax = PrincipalAxes()
        #prin_ax.t_axis = Axis(db.get('taxazm'),db.get('taxplg'))
        #prin_ax.p_axis = Axis(db.get('paxazm'),db.get('paxplg'))
        prin_ax.t_axis = Axis(db['taxazm'], db['taxplg'])
        prin_ax.p_axis = Axis(db['paxazm'], db['paxplg'])
        
        fm.nodal_planes = nps
        fm.principal_axes = prin_ax

        author_string = ':'.join([db['algorithm'], db['auth']])
        fm.creation_info = CreationInfo(
            version = db.get('mechid'), 
            creation_time = UTCDateTime(db['lddate']), 
            agency_id = self.agency,
            author = author_string,
            ) 
        
        fm.resource_id = self._rid(fm)
        return fm
    
    def _origins(self, relation):
        """
        Return lists of obspy Origins from a Relation of records
        in an origin-origerr join
        
        Inputs
        ------
        relation : iterable sequence of dict-like database records

        Returns : list of obspy.core.event.Origin
        -------

        """
        origins = []
        for dbtuple in relation:
            origins.append(self._map_join2origin(dbtuple))
        return origins

    def _phases(self, relation):
        """
        Return lists of obspy Arrivals and Picks from a Relation
        of records in an assoc-arrival join
        
        Inputs
        ------
        relation : iterable sequence of dict-like database records

        Returns : picks, arrivals
        -------
        picks    : list of obspy.core.event.Pick
        arrivals :  list of obspy.core.event.Arrival

        """
        picks = []
        arrivals = []
        for dbtuple in relation:
            p, a = self._map_join2phase(dbtuple)
            picks.append(p)
            arrivals.append(a)
        return picks, arrivals

    def _focalmechs(self, relation):
        """
        Return list of ObsPy FocalMech objects from an iterator
        of database records with dictionary access.

        """
        fmlist = []
        for fmline in relation:
            fmlist.append(self._map_fplane2focalmech(fmline))
        return fmlist
   
    def get_focalmechs(self, orid=None):
        cmd = ['dbopen fplane', 'dbsubset orid=={0}'.format(orid)]
        curs = self.cursor()
        rec = curs.execute('process', [cmd] )
        return self._focalmechs(curs)

    def get_origins(self, orid=None, evid=None):
        """
        Returns Origin instances from an orid or evid
        
        Inputs
        ------
        int of orid or evid

        Returns : list of obspy.core.event.Origin

        """
        if orid is not None:
            substr = 'dbsubset orid=={0}'.format(orid)
        elif evid is not None:
            substr = 'dbsubset evid=={0}'.format(evid)
        else:
            raise ValueError("Need to specify an ORID or EVID")
        
        cmd = ['dbopen origin', 'dbjoin -o origerr', substr, 'dbsort lddate']
        curs = self.cursor()
        rec = curs.execute('process', [cmd] )
        return self._origins(curs)
    
    def get_magnitudes(self, orid=None):
        """
        Return list of obspy event Magnitudes from a origin ID number
        
        Inputs
        ------
        orid : int of orid

        Returns : list of obspy.core.event.Magnitude

        Right now, looks in 'netmag', then 'origin', and assumes anything in netmag
        is in 'origin', that may or may not be true...
        """
        # FUTURE: Possibly implement as outer join netmag to origin and THEN
        #         check for magid/magnitude - else try ml/mb/ms
        mags = []
        substr = 'dbsubset orid=={0}'.format(orid)
        curs = self.cursor()
        # 1. Check netmag table
        rec = curs.execute('process', (['dbopen netmag', substr],) )
        if rec:
            for db in curs:
                mags.append(self._map_netmag2magnitude(db))
        else:
            # 2. Check the origin table for the 3 types it holds
            rec = curs.execute('process', (['dbopen origin', substr],) )
            db = curs.fetchone()
            for mtype in ('ml', 'mb', 'ms'):
                if db.get(mtype):
                    mags.append(self._map_origin2magnitude(db, mtype=mtype))
        return mags

    def get_phases(self, orid=None):
        """
        Return lists of obspy Arrivals and Picks from an ORID
        
        Inputs
        ------
        int of ORID

        Returns : picks, arrivals
        -------
        picks    : list of obspy.core.event.Pick
        arrivals :  list of obspy.core.event.Arrival

        """
        # Get associated picks
        #
        # took out 'dbjoin snetsta' and 'dbjoin schanloc'
        # schanloc wouldn't join right (need theta join), and not all dbsnapshots have snetsta access. WTF.
        # NOTE Try affiliation?? Didn't work for test db, but yes for the archive... WTF?
        #
        # Leaving the affiliation as an outer join - don't toss picks b/c we don't have a net code. Onward.
        #
        cmd = ['dbopen assoc', 'dbsubset orid=={0}'.format(orid), 'dbjoin arrival', 'dbjoin -o affiliation']
        curs = self.cursor()
        rec = curs.execute('process', [cmd] )
        return self._phases(curs)

    def _build(self, orid=None, origin=True, phases=False, focals=False, **kwargs):
        """
        Creates an ObsPy Event object from an Antelope Datascope database
        
        Inputs
        ------
        orid       : int of CSS3.0 Origin ID
        origin     : bool of whether to include location / mag  (True)
        phases     : bool of whether to include associated picks (False)
        focals     : bool of whether to include focal mechansims (False)
        
        Optional kwargs
        ---------------
        event_type : str of QuakeML accepted type of event
        anss       : dict of key/values of ANSS QuakeML attributes

        """
        # for now, take the most recent origin (sorted by mod time)
        #
        #  EVID not used, for now. In future, evid w/o orid returns all origins...
        #
        # build Origin and list of Magnitude objects
        if origin:
            origins = self.get_origins(orid)
            maglist = self.get_magnitudes(orid)
            # Should only be one, now
            origin = origins[-1]
            # If mags were calculated, slap the origin on them.
            if maglist:
                for m in maglist:
                    m.origin_id = origin.resource_id
                self.event.magnitudes = maglist
                self.event.preferred_magnitude_id = maglist[0].resource_id.resource_id
        # Add other data objects
        if phases:
            self.event.picks, origin.arrivals = self.get_phases(orid)
        if focals:
            #event.focal_mechanisms = self.get_focalmechs(orid)
            pass 
        self.event.origins = origins
        self.event.preferred_origin_id = origin.resource_id.resource_id
        self.event.creation_info = origin.creation_info.copy()
        self.event.creation_info.version = self._evid(orid)
        self.event.resource_id = self._rid(self.event)
        # Try to set an event type, if none, check the etype flag for preferred origin        
        if 'event_type' in kwargs:
            self.event.event_type = kwargs['event_type']
        else:
            self.event.event_type = self.origin_event_type(origin)
        # Possible to pass anss extras directly as kwarg
        if 'anss' in kwargs:
            self.event.extra = self.extra_anss(**kwargs['anss']) 
   
    def build(self, **kwargs):
        """
        Creates an ObsPy Event object from an Antelope Datascope database
        
        Currently, passing just an orid is handled, by creating a new event.
        
        FUTURE:
        Ideally, an evid would add all origins, and a new origin could be
        appended to an existing event, and made the preferred one.
        
        Inputs
        ------
        orid       : int of CSS3.0 Origin ID
        origin     : bool of whether to include location / mag  (True)
        phases     : bool of whether to include associated picks (False)
        focals     : bool of whether to include focal mechansims (False)
        
        Optional kwargs
        ---------------
        event_type : str of QuakeML accepted type of event
        anss       : dict of key/values of ANSS QuakeML attributes

        """
        self._build(**kwargs)

    @property
    def catalog(self):
        """
        Add existing Event to a Catalog

        """
        c = Catalog(events=[self.event])
        c.creation_info = CreationInfo(
            creation_time = UTCDateTime(), 
            agency_id     = self.agency,
            version       = self.event.creation_info.version,
            )
        c.resource_id = self._rid(c)
        return c

    @staticmethod
    def _qmls(c):
        """
        Writes Catalog object to QuakeML string

        Inputs
        ------
        c : obspy.core.event.Catalog

        Returns : str of QuakeML file contents

        """
        return Pickler().dumps(c)

    def quakeml_str(self):
        return self._qmls(self.catalog)

#--- Main Functions -------------------------------------------------------
def db2event(database, *args, **kwargs):
    """
    Convenience fucntion for EventConverter class
    See inline doc for CSSEventConverter.event() method
    
    Inputs
    ------
    database : str or antelope.datascope.Dbptr of database
    **kwargs : keyword args to be passed to event method
    
    Returns : obspy.core.event.Event instance
    
    """
    with CSSEventConverter(database) as dbc:
        dbc.build(*args, **kwargs)
    return dbc.event

def make_catalog(database, **kwargs):
    """
    Return an ObsPy Catalog object (eventParameter in QuakeML)
    
    This is a convenience function, just a Catalog wrapper which calls
    the event method, puts it in a Catalog.events list, and just puts
    a CreationInfo and ResourceIdentifier in there.
    
    Inputs
    ------
    database   : str or antelope.datascope.Dbptr to database
    orid       : int of CSS3.0 Origin ID
    origin     : bool of whether to include location / mag  (True)
    phases     : bool of whether to include associated picks (False)
    focals     : bool of whether to include focal mechansims (False)
    
    Optional kwargs
    ---------------
    event_type : str of QuakeML accepted type of event
    anss       : dict of key/values of ANSS QuakeML attributes

    Returns
    -------
    obspy.core.event.Catalog
    
    """
    with CSSEventConverter(database) as dbc:
        dbc.build(*args, **kwargs)
        c = dbc.catalog
    return c


class QuakeMLConverter(CSSEventConverter):
    
    def __str__(self):
        return self.quakeml_str(self.catalog)

