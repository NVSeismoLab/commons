# -*- coding: utf-8 -*-
"""
db2quakemlconverter.py 

    Mark C. Williams (2013)
    Nevada Seismological Laboratory

Contains methods to facilitate QuakeML generation including a factory
function for ResourceIdentifiers, and methods to generate QuakeML 
filenames and ANSS attributes.


Functions
=========
quakeml_rid(converter, obj): ResourceIdentifier factory function

    This function adheres to the 'rid_factory' convention of taking
    an instance object being ID'd, and returning a ResourceIdentifier
    based on the object properties. Currently implemented as an
    instancemethod.


Classes
=======
DBToQuakemlConverter : converter class
    
 This DBToQuakemlConverter class inherits from AntelopeToEventConverter,
 and contains methods to build an Event from an Antelope database
 and write out a QuakeML string. See class docstring for details.

"""
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.event import (Event, CreationInfo, Magnitude,
                              ResourceIdentifier)
from nsl.obspy.patches.quakeml import Pickler
from nsl.converters.antelope2eventconverter import AntelopeToEventConverter


def quakeml_rid(converter, obj, authority='local'):
    """
    ResourceIdentifier factory for making ID's for Event objects
    to produce valid QuakeML/ANSS files for USGS.
    
    Inputs
    ------
    converter : 'self' QuakemlConverter for using as instancemethod
    obj : str or obspy.core.event class instance
    authority : string of an auth_id, e.g. 'nn.anss.org'

    Returns
    -------
    obspy.core.event.ResourceIdentifier with 'resource_id' of:

    Notes
    -----
    if obj:
    is an event object (like a Pick, MomentTensor, etc)
        => id is "quakeml:<authority>/<ClassName>/<creation_info.version>
    is a string
        => append the string to "quakeml:<authority>/"
    
    Currently, a Magnitude is a special case, if there is no
    magid, a Magnitude will get the orid as its version, which must
    be combined with the magnitude type to produce a unique id.
    
    """
    if converter.auth_id:
        authority = converter.auth_id
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


class DBToQuakemlConverter(AntelopeToEventConverter):
    """
    Antelope -> Event converter with customizations for writing QuakeML files
    
    Methods
    -------
    build(self, evid=None, orid=None, delete=False, phase_data=False, focal_data=False):
        Build up an Event using various parameters
    quakeml_str(): Return QuakeML string of the current Event object
    quakeml_anss_attrib(self, evid=None): Construct dict of ANSS attributes
    quakeml_filename(self, product): Try to construct a meaningful XML filename

    """
    rid_factory = quakeml_rid

    def quakeml_anss_attrib(self, evid=None):
        """
        Returns stuff necessary for quakeml files
        
        These things are specific to a datacenter, in an effort to generalize
        the actual writer function as much as possible.
        
        Input
        -----
        evid   : int of some event identifier to name the file 
        agency : str of name or code of agency creating file (netcode)
        
        Returns : dict of the 4 ANSS 'catalog' attributes with meaningful values.
        """
        agency_code = self.agency.lower()
        if evid:
            anss_id = '{0:08d}'.format(evid)
        else:
            anss_id = '00000000'
        return {'datasource' : agency_code, 'dataid' : agency_code + anss_id, 'eventsource' : agency_code, 'eventid' : anss_id}

    def quakeml_filename(self, product):
        return self.event.extra['dataid']['value'] + '_' + product + '.xml'

    @staticmethod
    def extra_anss(**kwargs):
        """
        Create an dictionary for ANSS vars for use by event classes 'extra' attribute
        
        Inputs
        ------
        kwargs SHOULD be one of ('datasource','dataid','eventsource','eventid')
        
        Returns : dict of obspy 'extra' format

        """
        # _namespace renamed to namespace in new "extra" patch, use both for now
        extra_attrib = {} 
        ns_anss = ['catalog', 'http://anss.org/xmlns/catalog/0.1'] 
        for a in kwargs:
            extra_attrib[a] = {'value': kwargs[a],
                               'namespace': ns_anss, 
                               '_namespace': ns_anss, 
                               '_type': 'attribute'}
        return extra_attrib

    def build(self, evid=None, orid=None, delete=False, phase_data=False, focal_data=False):
        """
        Build up an Event object
    
        Inputs
        ------
        evid       : int of EVID
        orid       : int of ORID
        delete     : bool of whether to mark event deleted (False)
        phase_data : bool of whether to include phase arrivals for event (False)
        focal_data : bool of whether to look for focal mechanisms (False)

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
        """
        Return QuakeML string of current Event object

        :returns: str of QuakeML file contents

        """
        return self._qmls(self.catalog)
