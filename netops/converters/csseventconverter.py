#
"""
# csseventconverter.py 
# -by Mark C. Williams (2013), Nevada Seismological Laboratory
# 2013-2-13
#
# functions to map CSS3.0 to QuakeML schema
# (obspy Event class which can write QuakeML XML)
#
# Required     'obspy'    ObsPy (version with event, quakeml support)

Classes
=======

CSSEventConverter : methods to convert CSS to QuakeML schema


"""
import math
from quakeml import Pickler
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.event import (Catalog, Event, Origin, CreationInfo, Magnitude,
    EventDescription, OriginUncertainty, OriginQuality, CompositeTime,
    ConfidenceEllipsoid, StationMagnitude, Comment, WaveformStreamID, Pick,
    QuantityError, Arrival, FocalMechanism, MomentTensor, NodalPlanes,
    PrincipalAxes, Axis, NodalPlane, SourceTimeFunction, Tensor, DataUsed,
    ResourceIdentifier, StationMagnitudeContribution)

def _utc(timestamp):
    """Returns the UTCDateTime"""
    try:
        return UTCDateTime(timestamp)
    except:
        return None

def _str(item):
    """Return a string no matter what"""
    if item is not None:
        return str(item)
    else:
        return ''

def _km2m(dist):
    """Convert from km to m only if dist is not None"""
    if dist is not None:
        return dist * 1000.
    else:
        return None

def _m2deg_lat(dist):
    return dist / 110600.

def _m2deg_lon(dist, lat=0.):
    M = 6367449.
    return dist / (math.pi / 180.) / M / math.cos(math.radians(lat))

def _eval_ellipse(a, b, angle):
    return a*b/(math.sqrt((b*math.cos(math.radians(angle)))**2 +
                          (a*math.sin(math.radians(angle)))**2))

def get_n_e_on_ellipse(A, B, strike):
    """
    Return the solution for points N and E on an ellipse
    
    A : float of major axis diameter
    B : float of minor axis diameter
    strike : angle of major axis from North

    Returns
    -------
    n, e : floats of ellipse solution at north and east
    """
    n = _eval_ellipse(A/2, B/2, strike)
    e = _eval_ellipse(A/2, B/2, strike-90)
    return n, e


class CSSEventConverter(object):
    """
    Converter to build an ObsPy Event instance from CSS3.0 database

    Attributes
    ----------
    auth_id : str of authority URL (publicID)
    agency  : str of short agency identifier (net code)
    event   : obspy.core.event.Event current instance (blank Event)
    catalog : obspy.core.event.Catalog containing current Event 

    Methods
    -------
    build          : build an Event given some parameters (ORID)
    quakeml_str    : write the current Event out as QuakeML
    extra_anss     : return properly formatted 'extra' dict for ANSS QuakeML
    get_event_type : static class method to convert CSS origin type flag

    """
    #connection = None # DBAPI2 database connection
    event   = None    # event instance
    auth_id = 'local' # publicID, authority URL
    agency  = 'XX'    # agency ID, ususally net code

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
    
    def __init__(self, *args, **kwargs):
        """
        Set event
        """
        self.event = Event()
        
        for key in kwargs:
            if hasattr(self, key):
                setattr(self, key, kwargs[key])

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_tb):
        if hasattr(self.connection,'__exit__'): 
            self.connection.__exit__(ex_type, ex_value, ex_tb)
        else:
            try:
                self.connection.close()
            except:
                pass

    @property
    def _prefix(self):
        """Return a prefix for a custom RID"""
        return "smi:" +  self.auth_id
    
    def _rid(self, obj):
        """
        Return generic unique ResourceID
        
        With no pf or custom function available, will produce a 
        ResourceIdentifier exactly like the ObsPy default for a
        QuakeML file.

        """
        return ResourceIdentifier(prefix=self._prefix)
    
    def _map_join2origin(self, db):
        """
        Returns an Origin instance from a Dbtuple
        
        Inputs
        ------
        db :  dict of an origin-origerr joined record

        Returns : obspy.core.event.Origin

        """ 

        quality = OriginQuality(
            associated_phase_count = db.get('nass'),
            used_phase_count       = db.get('ndef'),
            standard_error         = db.get('sdobs'),
            )

        origin               = Origin()
        origin.latitude      = db.get('lat')
        origin.longitude     = db.get('lon')
        origin.depth         = _km2m(db.get('depth'))
        origin.time          = _utc(db.get('time'))
        origin.quality       = quality
        origin.creation_info = CreationInfo(
            creation_time = _utc(db.get('lddate')),
            agency_id     = self.agency, 
            version       = db.get('orid'),
            )
        
        # Solution Uncertainties
        # in CSS the ellipse is projected onto the horizontal plane
        # using the covariance matrix
        uncertainty = OriginUncertainty()
        a = _km2m(db.get('smajax'))
        b = _km2m(db.get('sminax'))
        s = db.get('strike')
        dep_u = _km2m(db.get('sdepth'))
        time_u = db.get('stime')

        uncertainty.max_horizontal_uncertainty = a
        uncertainty.min_horizontal_uncertainty = b
        uncertainty.azimuth_max_horizontal_uncertainty = s
        uncertainty.horizontal_uncertainty = a
        uncertainty.preferred_description = "horizontal uncertainty"

        if db.get('conf') is not None:
            uncertainty.confidence_level = db.get('conf') * 100.  

        origin.origin_uncertainty = uncertainty

        # Parameter Uncertainties 
        if all([a, b, s]):
            n, e = get_n_e_on_ellipse(a, b, s)
            lat_u = _m2deg_lat(n)
            lon_u = _m2deg_lon(e, lat=origin.latitude)
            origin.latitude_errors = {'uncertainty': lat_u} 
            origin.longitude_errors = {'uncertainty': lon_u}
        if dep_u:
            origin.depth_errors = {'uncertainty': dep_u}
        if time_u:
            origin.time_errors = {'uncertainty': time_u}


        if 'orbassoc' in _str(db.get('auth')):
            origin.evaluation_mode   = "automatic"
            origin.evaluation_status = "preliminary"
        else:
            origin.evaluation_mode   = "manual"
            origin.evaluation_status = "reviewed"
        # Save etype in a comment due to schema differences...
        etype_comment = Comment(
            resource_id = ResourceIdentifier(self._prefix+"/comment/etype/"+_str(db.get('orid'))),
            text        = _str(db.get('etype'))
            )
        origin.comments = [etype_comment]
        origin.resource_id = self._rid(origin)
        return origin

    def _map_netmag2magnitude(self, db):
        """Get Magnitude from dict of a netmag record"""
        m = Magnitude()
        m.mag             = db.get('magnitude')
        m.magnitude_type  = db.get('magtype')
        m.station_count   = db.get('nsta')
        m.creation_info   = CreationInfo(
            creation_time = _utc(db.get('lddate')),
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
        """Get Magnitude from dict of an origin record"""
        m = Magnitude()
        m.mag             = db.get(mtype)
        m.magnitude_type  = mtype 
        m.creation_info   = CreationInfo(
            creation_time = _utc(db.get('lddate')), 
            agency_id     = self.agency,
            version       = db.get('orid'),
        	author        = db.get('auth'),
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
        p.time = _utc(db.get('time'))
        css_chan = db.get('chan')
        p.waveform_id = WaveformStreamID(station_code = db.get('sta'), 
                                         channel_code = db.get('fchan', css_chan),
                                         network_code = db.get('net'),
                                         location_code = db.get('loc'),
                                         )
        p.horizontal_slowness = db.get('slow')
        p.horizontal_slowness_errors = self._create_dict(db, 'delslo')
        p.backazimuth = db.get('azimuth')
        p.backazimuth_errors = self._create_dict(db, 'delaz')
        
        on_qual = _str(db.get('qual')).lower()
        if 'i' in on_qual:
            p.onset = "impulsive"
        elif 'e' in on_qual:
            p.onset = "emergent"
        elif 'w' in on_qual:
            p.onset = "questionable"
        else:
            p.onset =  None
        
        p.phase_hint = db.get('iphase')
        
        pol = _str(db.get('fm')).lower()
        if 'c' in pol or 'u' in pol:
            p.polarity = "positive"
        elif 'd' in pol or 'r' in pol:
            p.polarity = "negative"
        elif '.' in pol:
            p.polarity = "undecidable"
        else:
            p.polarity = None
        
        p.evaluation_mode = "automatic"
        if 'orbassoc' not in _str(db.get('auth')):
            p.evaluation_mode = "manual"
        
        p.evaluation_status = "preliminary"
        if p.evaluation_mode is "manual":
            p.evaluation_status = "reviewed"
        
        p.creation_info = CreationInfo(
            version = db.get('arid'), 
            creation_time = _utc(db.get('arrival.lddate')), 
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
        a.earth_model_id = ResourceIdentifier(self._prefix+'/VelocityModel/'+_str(db.get('vmodel')))
        a.creation_info = CreationInfo(
            version = db.get('arid'), 
            creation_time = _utc(db.get('lddate')),
            agency_id = self.agency,
            )
        # Save timedef in a comment due to schema differences...
        assoc_str = _str(db.get('arid')) + '-' + _str(db.get('orid'))
        timedef_comment = Comment(
            resource_id = ResourceIdentifier(self._prefix + "/comment/timedef/" + assoc_str),
            text        = _str(db.get('timedef'))
            )
        a.comments = [timedef_comment]
        a.resource_id = self._rid(a)
        return p, a

    def _map_fplane2focalmech(self, db):
        """
        Maps fplane record to a FocalMechanism

        """
        #
        # NOTE: Antelope schema for this is wrong, no nulls defined
        #       so no 'get' access for now...
        #
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

