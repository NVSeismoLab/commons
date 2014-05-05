# -*- coding: utf-8 -*-
"""
css2eventconverter.py

    Mark C. Williams (2013)
    Nevada Seismological Laboratory
    2013-02-13

    Converter class to map CSS3.0 to QuakeML schema
    (converts to obspy Event class which can write QuakeML XML)


Classes
=======
CSSToEventConverter : methods to convert CSS to QuakeML schema

Required
--------
'obspy' : ObsPy (version with event, quakeml support)

"""
import math
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.event import (Catalog, Event, Origin, CreationInfo, Magnitude,
    EventDescription, OriginUncertainty, OriginQuality, CompositeTime,
    ConfidenceEllipsoid, StationMagnitude, Comment, WaveformStreamID, Pick,
    QuantityError, Arrival, FocalMechanism, MomentTensor, NodalPlanes,
    PrincipalAxes, Axis, NodalPlane, SourceTimeFunction, Tensor, DataUsed,
    ResourceIdentifier, StationMagnitudeContribution)


CSS_NAMESPACE = ('css',"http://www.seismo.unr.edu/schema/css3.0")


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


def _get_NE_on_ellipse(A, B, strike):
    """
    Return the solution for points N and E on an ellipse
    
    A : float of semi major axis
    B : float of semi minor axis
    strike : angle of major axis from North

    Returns
    -------
    n, e : floats of ellipse solution at north and east
    """
    n = _eval_ellipse(A, B, strike)
    e = _eval_ellipse(A, B, strike-90)
    return n, e


class CSSToEventConverter(object):
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
    rid_factory = None # function(object, authority)
    
    event   = None    # event instance
    
    auth_id = 'local' # publicID, authority URL
    agency  = 'XX'    # agency ID, ususally net code

    @staticmethod 
    def get_event_type(etype, etype_map=None):
        """
        Map a CSS3.0 etype origin flag to a QuakeML event type
        
        Default dictionary will be updated by anything in 'etype_map'

        Inputs
        ------
        etype : str of a valid etype
        etype_map: dict of {etype: eventType} added to standard css3.0 one

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
        if etype_map:
            event_type_map.update(etype_map)
        # Try to find a direct match, then check for stuff like 'LF'
        if etype.lower() in event_type_map:
            return event_type_map[etype.lower()]
        else:
            for k,v in event_type_map.items():
                if k in etype.lower():
                    return v
    
    @classmethod
    def origin_event_type(cls, origin, emap=None):
        """Return a proper event_type from a CSS3.0 etype flag stored in an origin"""
        if hasattr(origin, 'extra') and 'etype' in origin.extra:
            etype = origin.extra['etype']['value']
            return cls.get_event_type(etype, etype_map=emap)
        else:
            return "not reported"
    
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
            return {field : value}
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

    @property
    def _prefix(self):
        """Return a prefix for a custom RID"""
        return "smi:" +  self.auth_id
    
    def _rid(self, obj=None):
        """
        Return unique ResourceID
        
        With no custom function available, will produce a 
        ResourceIdentifier exactly like the ObsPy default for a
        QuakeML file.
        """
        if self.rid_factory is None:
            return ResourceIdentifier(prefix=self._prefix)
        else:
            return self.rid_factory(obj, self.auth_id)
    
    def _map_join2origin(self, db):
        """
        Return an Origin instance from an dict of CSS key/values
        
        Inputs
        ======
        db : dict of key/values of CSS fields related to the origin (see Join)

        Returns
        =======
        obspy.core.event.Origin

        Notes
        =====
        Any object that supports the dict 'get' method can be passed as
        input, e.g. OrderedDict, custom classes, etc.
        
        Join
        ----
        origin <- origerr (outer)

        """ 
        #-- Basic location ------------------------------------------
        origin = Origin()
        origin.latitude = db.get('lat')
        origin.longitude = db.get('lon')
        origin.depth = _km2m(db.get('depth'))
        origin.time = _utc(db.get('time'))
        origin.creation_info = CreationInfo(
            creation_time = _utc(db.get('lddate')),
            agency_id = self.agency, 
            version = db.get('orid'),
            )
        origin.extra = {}
        
        #-- Quality -------------------------------------------------
        quality = OriginQuality(
            associated_phase_count = db.get('nass'),
            used_phase_count = db.get('ndef'),
            standard_error = db.get('sdobs'),
            )
        origin.quality = quality

        #-- Solution Uncertainties ----------------------------------
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

        if uncertainty.horizontal_uncertainty is not None:
            origin.origin_uncertainty = uncertainty

        #-- Parameter Uncertainties ---------------------------------
        if all([a, b, s]):
            n, e = _get_NE_on_ellipse(a, b, s)
            lat_u = _m2deg_lat(n)
            lon_u = _m2deg_lon(e, lat=origin.latitude)
            origin.latitude_errors = {'uncertainty': lat_u} 
            origin.longitude_errors = {'uncertainty': lon_u}
        if dep_u:
            origin.depth_errors = {'uncertainty': dep_u}
        if time_u:
            origin.time_errors = {'uncertainty': time_u}

        #-- Analyst-determined Status -------------------------------
        posted_author = _str(db.get('auth'))
        
        origin.evaluation_mode = "automatic"
        origin.evaluation_status = "preliminary"
        if posted_author and 'orbassoc' not in posted_author:
            origin.evaluation_mode = "manual"
            origin.evaluation_status = "reviewed"
        # Save etype per origin due to schema differences...
        css_etype = _str(db.get('etype'))
        # Compatible with future patch rename "_namespace" -> "namespace"
        origin.extra['etype'] = {
            'value': css_etype, 
            '_namespace': CSS_NAMESPACE,  # TBDepricated, remove
            'namespace': CSS_NAMESPACE
            }

        origin.resource_id = self._rid(origin)
        return origin

    def _map_netmag2magnitude(self, db):
        """
        Return an obspy Magnitude from an dict of CSS key/values
        corresponding to one record.
        
        Inputs
        ======
        db : dict of key/values of CSS fields from the 'netmag' table

        Returns
        =======
        obspy.core.event.Magnitude

        Notes
        =====
        Any object that supports the dict 'get' method can be passed as
        input, e.g. OrderedDict, custom classes, etc.
        """
        m = Magnitude()
        m.mag = db.get('magnitude')
        m.magnitude_type = db.get('magtype')
        m.station_count = db.get('nsta')
        m.creation_info = CreationInfo(
            creation_time = _utc(db.get('lddate')),
            agency_id = self.agency,
            version = db.get('magid'),
            author = db.get('auth'),
            )
        if m.creation_info.author.startswith('orb'):
            m.evaluation_status = "preliminary"
        else:
            m.evaluation_status = "reviewed"
        m.resource_id = self._rid(m)
        return m

    def _map_origin2magnitude(self, db, mtype='ml'):
        """
        Return an obspy Magnitude from an dict of CSS key/values
        corresponding to one record.
        
        Inputs
        ======
        db : dict of key/values of CSS fields from the 'origin' table

        Returns
        =======
        obspy.core.event.Magnitude

        Notes
        =====
        Any object that supports the dict 'get' method can be passed as
        input, e.g. OrderedDict, custom classes, etc.
        """
        m = Magnitude()
        m.mag = db.get(mtype)
        m.magnitude_type = mtype 
        m.creation_info = CreationInfo(
            creation_time = _utc(db.get('lddate')), 
            agency_id = self.agency,
            version = db.get('orid'),
        	author = db.get('auth'),
            )
        if m.creation_info.author.startswith('orb'):
            m.evaluation_status = "preliminary"
        else:
            m.evaluation_status = "reviewed"
        m.resource_id = self._rid(m)
        return m

    def _map_join2phase(self, db):
        """
        Return an obspy Arrival and Pick from an dict of CSS key/values
        corresponding to one record. See the 'Join' section for the implied
        database table join expected.
        
        Inputs
        ======
        db : dict of key/values of CSS fields related to the phases (see Join)

        Returns
        =======
        obspy.core.event.Pick, obspy.core.event.Arrival

        Notes
        =====
        Any object that supports the dict 'get' method can be passed as
        input, e.g. OrderedDict, custom classes, etc.
        
        Join
        ----
        assoc <- arrival <- affiliation (outer) <- schanloc [sta chan] (outer)
        
        """
        p = Pick()
        p.time = _utc(db.get('time'))
        def_net = self.agency[:2].upper()
        css_sta = db.get('sta')
        css_chan = db.get('chan')
        p.waveform_id = WaveformStreamID(
            station_code = db.get('fsta') or css_sta, 
            channel_code = db.get('fchan') or css_chan,
            network_code = db.get('snet') or def_net,
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

        a = Arrival()
        a.pick_id = ResourceIdentifier(str(p.resource_id), referred_object=p)
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
        a.extra = {}
        timedef = _str(db.get('timedef'))
        # Save timedef in a comment due to schema differences...
        # TODO: DEPRICATE ---------------------------------------->>>
        assoc_str = _str(db.get('arid')) + '-' + _str(db.get('orid'))
        timedef_comment = Comment(
            resource_id = ResourceIdentifier(self._prefix + "/comment/timedef/" + assoc_str),
            text = timedef
            )
        a.comments = [timedef_comment]
        #--------------------------------------------------------->>>
        a.extra['timedef'] = {
            'value': timedef, 
            '_namespace': CSS_NAMESPACE,
            'namespace': CSS_NAMESPACE
            }
        a.resource_id = self._rid(a)
        return p, a

    def _map_fplane2focalmech(self, db):
        """
        Return an obspy FocalMechanism from an dict of CSS key/values
        corresponding to one record. See the 'Join' section for the implied
        database join expected.
        
        Inputs
        ======
        db : dict of key/values of CSS fields from the 'fplane' table

        Returns
        =======
        obspy.core.event.FocalMechanism

        Notes
        =====
        Any object that supports the dict 'get' method can be passed as
        input, e.g. OrderedDict, custom classes, etc.

        """
        #
        # NOTE: Antelope schema for this is wrong, no nulls defined
        # 
        fm = FocalMechanism()

        nps = NodalPlanes()
        nps.nodal_plane_1 = NodalPlane(db.get('str1'), db.get('dip1'), db.get('rake1'))
        nps.nodal_plane_2 = NodalPlane(db.get('str2'), db.get('dip2'), db.get('rake2'))

        nps.preferred_plane = 1

        prin_ax = PrincipalAxes()
        prin_ax.t_axis = Axis(db.get('taxazm'),db.get('taxplg'))
        prin_ax.p_axis = Axis(db.get('paxazm'),db.get('paxplg'))

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

    @staticmethod
    def _nearest_cities_description(nearest_string):
        """
        Return an EventDescription of type 'nearest cities'

        Inputs
        ------
        nearest_string : str of decription for the text field
        """
        return EventDescription(nearest_string, "nearest cities")

    @property
    def catalog(self):
        """
        Add existing Event to a Catalog

        """
        c = Catalog(events=[self.event])
        c.creation_info = CreationInfo(
            creation_time = UTCDateTime(), 
            agency_id = self.agency,
            version = self.event.creation_info.version,
            )
        c.resource_id = self._rid(c)
        return c

