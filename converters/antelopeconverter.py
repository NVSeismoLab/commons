#    
from csseventconverter import CSSEventConverter
from curds2 import connect, OrderedDictRow

class AntelopeEventConverter(CSSEventConverter):
    """
    Extracts data in CSS schema from Antelope Datascope database
    and converts to (QuakeML) schema ObsPy Event.
    
    """

    def __init__(self, database, perm='r', *args, **kwargs):
        
        super(AntelopeEventConverter, self).__init__(*args, **kwargs)
        self.connection = connect(database, perm, row_factory=OrderedDictRow)
        self.connection.CONVERT_NULL = True

    def _evid(self, orid):
        """
        Return EVID from a known ORID
        
        Inputs
        ------
        int of orid

        Returns : int of evid

        """
        curs = self.connection.cursor(table='origin')
        n = curs.execute('find', ['orid=={0}'.format(orid)] )
        curs.scroll(n, 'absolute')
        db = curs.fetchone()
        return db['evid']
    
    def get_focalmechs(self, orid=None):
        cmd = ['dbopen fplane', 'dbsubset orid=={0}'.format(orid)]
        curs = self.connection.cursor()
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
        curs = self.connection.cursor()
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
        # Get associated picks
        #
        # took out 'dbjoin snetsta' and 'dbjoin schanloc'
        # schanloc wouldn't join right (need theta join), and not all dbsnapshots have snetsta access. WTF.
        # NOTE Try affiliation?? Didn't work for test db, but yes for the archive... WTF?
        #
        # Leaving the affiliation as an outer join - don't toss picks b/c we don't have a net code. Onward.
        #
        cmd = ['dbopen assoc', 'dbsubset orid=={0}'.format(orid), 'dbjoin arrival', 'dbjoin -o affiliation']
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
    with AntelopeEventConverter(database) as dbc:
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
    with AntelopeEventConverter(database) as dbc:
        dbc.build(*args, **kwargs)
        c = dbc.catalog
    return c


