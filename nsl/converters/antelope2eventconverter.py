# -*- coding: utf-8 -*-
"""
antelopeconverter.py 
    by Mark C. Williams (2013), Nevada Seismological Laboratory

This module contains a class with methods to produce an 
obspy.core.event.Event object from an Antelope database

It inherits from the CSSToEventConverter, and uses the
private conversion methods to map CSS to QuakeML.

The "get_*" methods contain Antelope-specific database
commands to get the data out of your db tables.

Classes
=======

AntelopeToEventConverter(database, perm, *args, **kwargs)

"""
from numpy import array
from obspy.core.util import gps2DistAzimuth
from curds2 import connect, OrderedDictRow, NamedTupleRow
from nsl.common.util import azimuth2compass
from nsl.obspy.util import add_quality_params_from_data
from nsl.converters.css2eventconverter import CSSToEventConverter
from nsl.antelope.pf import get_pf


class AntelopeToEventConverter(CSSToEventConverter):
    """
    Extracts data in CSS schema from Antelope Datascope database
    and converts to (QuakeML) schema ObsPy Event.

    Attributes
    ----------
    connection : DBAPI2 Database Connection instance
    place_db : str of a dbname with places12 schema
    emap : dict to store custom etype -> eventType mappings

    Methods
    -------
    get_origins    : return list of Origins from db
    get_magnitudes : return list of Magnitudes from db
    get_phases     : return lists of Pick/Arrivals from db
    get_focalmechs : return list of FocalMechanisms from db
    get_event      : build and return an Event

    Notes
    -----
    The four main 'get' methods (origin, mag, focalmech, and phases) contain
    the esoteric database calls. They then use the inherited methods from
    CSSEventConverter to create an obspy.core.event.Event from the
    database data.
    
    """
    connection = None  # DBAPI2 database connection
    
    place_db = None  # for looking up nearest places
    emap = {}  # for adding custom etypes
    
    @classmethod
    def load_pf(cls, pfname='db2quakeml'):
        try:
            pf = get_pf(pfname)
        except Exception:
            pf = {}
        finally:
            cls.agency = pf.get('AGENCY_CODE', 'XX') 
            cls.place_db = pf.get('PLACE_DB', None)
            cls.auth_id = pf.get('authority', 'local')
            cls.emap = pf.get('etypes',{})
            del pf

    def __init__(self, database, perm='r', **kwargs):
        """
        Initialize converter and connect to database
        
        Inputs
        ======
        database : str name of database
        **kwargs : extra keyword args

        kwargs
        ------
        perm : str of permissions ('r')
        pf : str name of pf file containing settings ('db2quakeml')

        """
        # Load config using Antelope-style param file
        if 'pf' in kwargs:
            _pf = kwargs.pop('pf')
        else:
            _pf = 'db2quakeml'
        self.load_pf(_pf)
        
        super(AntelopeToEventConverter, self).__init__(**kwargs)
        self.connection = connect(database, perm, row_factory=OrderedDictRow)
        self.connection.CONVERT_NULL = True
    
    def __enter__(self):
        """Instance for context support"""
        return self

    def __exit__(self, ex_type, ex_value, ex_tb):
        """
        Call database connection context exit method if exists.
        Otherwise try to close the connection
        """
        if hasattr(self.connection,'__exit__'): 
            self.connection.__exit__(ex_type, ex_value, ex_tb)
        else:
            try:
                self.connection.close()
            except:
                pass

    def _evid(self, orid):
        """
        Return EVID from a known ORID
        
        Inputs
        ------
        int of orid

        Returns : int of evid

        """
        curs = self.connection.cursor()
        nrecs = curs.execute.lookup(table='origin')
        n = curs.execute('find', ['orid=={0}'.format(orid)] )
        curs.scroll(n, 'absolute')
        db = curs.fetchone()
        return db['evid']
    
    def get_nearest_event_description(self, latitude, longitude, database=None):
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
            database = self.place_db
        try:
            curs = connect(database).cursor(row_factory=NamedTupleRow)
            nrecs = curs.execute.lookup(table='places')
            stats = array([gps2DistAzimuth(latitude, longitude, r.lat, r.lon) for r in curs])
            ind = stats.argmin(0)[0]
            minstats = stats[ind]
            curs.scroll(int(ind), 'absolute')
            minrec = curs.fetchone()
            dist, azi, backazi = minstats
            compass = azimuth2compass(backazi)
            place_info = {'distance': dist/1000., 'direction': compass, 'city': minrec.place, 'state': minrec.state}
            curs.close()
            s = "{distance:0.1f} km {direction} of {city}, {state}".format(**place_info)
            return self._nearest_cities_description(s)
        except:
            return None

    def get_focalmechs(self, orid=None):
        """
        Returns FocalMechanism instances of an ORID
        
        Inputs
        ------
        orid : int of ORID

        Returns
        -------
        list of obspy.core.event.FocalMechanisms

        """
        cmd = ['dbopen fplane', 'dbsubset orid=={0}'.format(orid)]
        curs = self.connection.cursor()
        rec = curs.execute('process', [cmd] )
        curs.CONVERT_NULL = False  # Antelope schema bug - missing fplane NULLS
        return self._focalmechs(curs)

    def get_origins(self, orid=None, evid=None):
        """
        Returns Origin instances from an ORID or EVID
        
        Inputs
        ------
        orid : int of ORID 
        evid : int of EVID

        Returns
        -------
        list of obspy.core.event.Origin

        """
        if orid is not None:
            substr = 'dbsubset orid=={0}'.format(orid)
        elif evid is not None:
            substr = 'dbsubset evid=={0}'.format(evid)
        else:
            raise ValueError("Need to specify an ORID or EVID")
        
        cmd = ['dbopen origin', 'dbjoin -o origerr', substr, 'dbsort lddate']
        curs = self.connection.cursor()
        rec = curs.execute('process', [cmd] )
        return self._origins(curs)
    
    def get_magnitudes(self, orid=None):
        """
        Return list of obspy event Magnitudes from a origin ID number
        
        Inputs
        ------
        orid : int of orid

        Returns
        -------
        list of obspy.core.event.Magnitude
        
        Notes
        -----
        Right now, looks in 'netmag', then 'origin', and assumes anything in netmag
        is in 'origin', that may or may not be true...
        """
        # FUTURE: Possibly implement as outer join netmag to origin and THEN
        #         check for magid/magnitude - else try ml/mb/ms
        mags = []
        substr = 'dbsubset orid=={0}'.format(orid)
        curs = self.connection.cursor()
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
        cmd = ['dbopen assoc', 'dbsubset orid=={0}'.format(orid),
               'dbjoin arrival', 'dbjoin -o snetsta',
               'dbjoin -o schanloc sta chan']
        curs = self.connection.cursor()
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
                self.event.preferred_magnitude_id = str(maglist[0].resource_id)
            # Add other data objects
            if phases:
                self.event.picks, origin.arrivals = self.get_phases(orid)
                add_quality_params_from_data(origin)
        if focals:
            focalmechs = self.get_focalmechs(orid)
            self.event.focal_mechanisms = focalmechs
            if focalmechs:
                self.event.preferred_focal_mechanism_id = str(focalmechs[-1].resource_id)
        self.event.origins = origins
        self.event.preferred_origin_id = str(origin.resource_id)
        self.event.creation_info = origin.creation_info.copy()
        self.event.creation_info.version = self._evid(orid)
        self.event.resource_id = self._rid(self.event)
        # Try to set an event type, if none, check the etype flag for preferred origin        
        if 'event_type' in kwargs:
            self.event.event_type = kwargs['event_type']
        else:
            self.event.event_type = self.origin_event_type(origin, emap=self.emap)
   
    def get_event(self, **kwargs):
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

        """
        self._build(**kwargs)
        return self.event


#--- Main Functions -------------------------------------------------------
def db2event(database, *args, **kwargs):
    """
    Inputs
    ------
    database : str or antelope.datascope.Dbptr of database
    **kwargs : keyword args to be passed to event method
    
    Returns : obspy.core.event.Event instance
    
    """
    with AntelopeToEventConverter(database) as dbc:
        ev = dbc.get_event(*args, **kwargs)
    return ev
