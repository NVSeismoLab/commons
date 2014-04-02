# -*- coding: utf-8 -*-
"""
# ichinose.py
# -by Mark (2013), Nevada Seismological Laboratory
# NSL Ichinose file Parser class
#
# contains class and fxns to make an ObsPy event
# from Gene Ichinose's moment tensor text output
# (specifically optimized for 'moment.php' files
# for now...
#
# Parser -> class which holds text and methods
#            to extract certain values of the mt inversion
#
"""
import re
from obspy.core.utcdatetime import UTCDateTime
from obspy.core.event import (Catalog, Event, Origin, CreationInfo, Magnitude,
    EventDescription, OriginUncertainty, OriginQuality, CompositeTime,
    ConfidenceEllipsoid, StationMagnitude, Comment, WaveformStreamID, Pick,
    QuantityError, Arrival, FocalMechanism, MomentTensor, NodalPlanes,
    PrincipalAxes, Axis, NodalPlane, SourceTimeFunction, Tensor, DataUsed,
    ResourceIdentifier, StationMagnitudeContribution)


def rid(obj):
    return ResourceIdentifier(prefix='smi:local')

class Parser(object):
    '''
    Parse the NSL Icinose email output 

    '''
    line = []

    def __init__(self, email_text, endline="\n"):
        '''
        Working data is a list of lines from the file
        '''
        if isinstance(email_text, file):
            email_text = email_text.read()
        self.line = email_text.split(endline)
    
    def _id(self, n):
        '''Pull out an integer ID'''
        return int(self.line[n].split(':')[-1])

    def _event_info(self, n):
        '''Pull out date/time lat lon from info line'''
        date, julday, time, lat, lon, orid = self.line[n].split()
        date = date.replace('/','-')
        utctime = UTCDateTime('T'.join([date,time]))
        latitude = float(lat)
        longitude = float(lon)
        orid = int(orid)
        return {'time': utctime, 'lat': latitude, 'lon': longitude, 'orid': orid }
        
    def _depth(self, n):
        '''Stub'''
        depth = re.findall('\d+\.\d+', self.line[n])[0]
        return float(depth)

    def _mt_sphere(self, n):
        '''
        Moment Tensor in Spherical coordinates
        Input  :  n (where n is line of title)
        Output :  dict of element/value of tensor
                  e.g. 'Mrr','Mtf' raised to 'EXP'-7 (N-m)
        '''
        line1  =  re.findall(r'...=(?:\s+\-?\d\.\d+|\d{2})', self.line[n+1])
        line1  += re.findall(r'...=(?:\s+\-?\d\.\d+|\d{2})', self.line[n+2])
        exp_str = line1.pop(-1)
        exp = int(exp_str.split('=')[1]) - 7 # N-m
        mt = dict(m.split('=') for m in line1)
        for k, v in mt.items():
            mt[k] = float(v) * 10**exp
        return mt

    def _mt_cart(self, n):
        '''
        Moment Tensor in Cartesian coordinates

        Take the three lines after n and build a 3x3 list of lists
        '''
        m = []
        for l in range(n+1,n+4):
            m.append([float(x) for x in self.line[l].split()])
        return m

    def _vectors(self, n):
        '''
        Return info on eigenvalues/vectors of princial axes (P,T,N)
        '''
        axes = {}
        for l in range(n+1,n+4):
            axis = {}
            name = re.findall(r'.\-axis', self.line[l])[0][0]
            ax_values = re.findall(r'\w+=(?:\s?\-?\d\.\d+|\d+)', self.line[l])
            for _a in ax_values:
                key, value = _a.split('=')
                value = float(value)
                axis[key] = value
            axes[name] = axis
        return axes

    def _gap(self, n):
        gap_exp, dist_exp = re.findall(r'\w+=\s?(?:\d+\.\d+|\d+)', self.line[n])
        gap  = gap_exp.split('=')[-1]
        dist = dist_exp.split('=')[-1]
        return float(gap)

    def _percent(self, n):
        perc = re.findall(r'(?:\d+\.\d+|\d+)\s?%',self.line[n])[0].split()[0]
        frac = float(perc)/100.
        return frac
    
    def _epsilon(self, n):
        '''Pull out epsilon variance'''
        return float(self.line[n].split('=')[-1])

    def _mw(self, n):
        return float(self.line[n].split()[-1])

    def _mo(self, n):
        '''
        Pull out scalar moment
        Output in N-m
        '''
        str_mo = re.findall(r'\d+\.\d+x10\^\d+', self.line[n])[0]
        str_mo = re.split(r'[x\^]',str_mo)
        mant = float(str_mo[0])
        bse  = int(str_mo[1])
        exp  = int(str_mo[2])
        exp -= 7 # convert from dyne-cm to Nm
        return mant*bse**exp

    def _double_couple(self, n):
        '''
        Line 'n' is line 'Major Double Couple'
        Return list of 2 [strike,dip,rake] lists of plane values
        '''
        values1 = self.line[n+2].split(':')[-1]
        values2 = self.line[n+3].split(':')[-1]
        plane1  = [float(x) for x in values1.split()]
        plane2  = [float(x) for x in values2.split()]
        return [plane1, plane2]
    
    def _number_of_stations(self, n):
        '''
        Extracts number of defining stations used
        '''
        ns = re.findall(r'Used=\d+', self.line[n])[0]
        return int(ns.split('=')[-1])

    def _creation_time(self, n):
        '''
        When file says it was made
        '''
        label, date, time = self.line[n].split()
        date = date.replace('/','-')
        return UTCDateTime('T'.join([date,time]))

    def run(self):
        '''
        In future, parse the file and have attributes available
        
        '''
        pass

def mt2event(filehandle, quakeml_rid=rid):
    '''Build an obspy moment tensor focal mech event

    This makes the tensor output into an Event containing:
    1) a FocalMechanism with a MomentTensor, NodalPlanes, and PrincipalAxes
    2) a Magnitude of the Mw from the Tensor

    Which is what we want for outputting QuakeML using
    the (slightly modified) obspy code.

    Input
    -----
    filehandle => open file OR str from filehandle.read()

    Output
    ------
    event => instance of Event() class as described above
    ''' 
    p = Parser(filehandle)
    event         = Event(event_type='earthquake')
    origin        = Origin()
    focal_mech    = FocalMechanism()
    nodal_planes  = NodalPlanes()
    moment_tensor = MomentTensor()
    principal_ax  = PrincipalAxes()
    magnitude     = Magnitude()
    data_used     = DataUsed()
    creation_info = CreationInfo(agency_id='NN')
    ev_mode = 'automatic'
    ev_stat = 'preliminary'
    evid = None
    orid = None
    # Parse the entire file line by line.
    for n,l in enumerate(p.line):
        if 'REVIEWED BY NSL STAFF' in l:
            ev_mode = 'manual'
            ev_stat = 'reviewed'
        if 'Event ID' in l:
            evid = p._id(n)
        if 'Origin ID' in l:
            orid = p._id(n)
        if 'Ichinose' in l:
            moment_tensor.category = 'regional'
        if re.match(r'^\d{4}\/\d{2}\/\d{2}', l):
            ev = p._event_info(n)
        if 'Depth' in l:
            derived_depth = p._depth(n)
        if 'Mw' in l:
            magnitude.mag = p._mw(n) 
            magnitude.magnitude_type = 'Mw'
        if 'Mo' in l and 'dyne' in l:
            moment_tensor.scalar_moment = p._mo(n)
        if 'Percent Double Couple' in l:
            moment_tensor.double_couple = p._percent(n)
        if 'Percent CLVD' in l:
            moment_tensor.clvd = p._percent(n)
        if 'Epsilon' in l:
            moment_tensor.variance = p._epsilon(n)
        if 'Percent Variance Reduction' in l:
            moment_tensor.variance_reduction = p._percent(n)
        if 'Major Double Couple' in l and 'strike' in p.line[n+1]:
            np = p._double_couple(n)
            nodal_planes.nodal_plane_1 = NodalPlane(*np[0])
            nodal_planes.nodal_plane_2 = NodalPlane(*np[1])
            nodal_planes.preferred_plane = 1
        if 'Spherical Coordinates' in l:
            mt = p._mt_sphere(n)
            moment_tensor.tensor = Tensor(
                m_rr = mt['Mrr'],
                m_tt = mt['Mtt'],
                m_pp = mt['Mff'],
                m_rt = mt['Mrt'],
                m_rp = mt['Mrf'],
                m_tp = mt['Mtf'],
                )
        if 'Eigenvalues and eigenvectors of the Major Double Couple' in l:
            ax = p._vectors(n)
            principal_ax.t_axis = Axis(ax['T']['trend'], ax['T']['plunge'], ax['T']['ev'])
            principal_ax.p_axis = Axis(ax['P']['trend'], ax['P']['plunge'], ax['P']['ev'])
            principal_ax.n_axis = Axis(ax['N']['trend'], ax['N']['plunge'], ax['N']['ev'])
        if 'Number of Stations' in l:
            data_used.station_count = p._number_of_stations(n)
        if 'Maximum' in l and 'Gap' in l:
            focal_mech.azimuthal_gap = p._gap(n)
        if re.match(r'^Date', l):
            creation_info.creation_time = p._creation_time(n)
    # Creation Time
    creation_info.version = orid
    # Fill in magnitude values
    magnitude.evaluation_mode = ev_mode
    magnitude.evaluation_status = ev_stat
    magnitude.creation_info = creation_info.copy()
    magnitude.resource_id = quakeml_rid(magnitude)
    # Stub origin
    origin.time = ev.get('time')
    origin.latitude = ev.get('lat')
    origin.longitude = ev.get('lon')
    origin.depth = derived_depth * 1000.
    origin.depth_type = "from moment tensor inversion"
    origin.creation_info = creation_info.copy()
     # Unique from true origin ID
    _oid = quakeml_rid(origin)
    origin.resource_id = ResourceIdentifier(_oid.resource_id + '/mt')
    del _oid
    # Make an id for the MT that references this origin
    ogid = origin.resource_id.resource_id
    doid = ResourceIdentifier(ogid, referred_object=origin)
    # Make an id for the moment tensor mag which references this mag
    mrid = magnitude.resource_id.resource_id
    mmid = ResourceIdentifier(mrid, referred_object=magnitude)
    # MT todo: could check/use URL for RID if parsing the php file
    moment_tensor.evaluation_mode = ev_mode
    moment_tensor.evaluation_status = ev_stat
    moment_tensor.data_used = data_used
    moment_tensor.moment_magnitude_id = mmid
    moment_tensor.derived_origin_id = doid
    moment_tensor.creation_info = creation_info.copy()
    moment_tensor.resource_id = quakeml_rid(moment_tensor)
    # Fill in focal_mech values
    focal_mech.nodal_planes  = nodal_planes
    focal_mech.moment_tensor = moment_tensor
    focal_mech.principal_axes = principal_ax
    focal_mech.creation_info = creation_info.copy()
    focal_mech.resource_id = quakeml_rid(focal_mech)
    # add mech and new magnitude to event
    event.focal_mechanisms = [focal_mech]
    event.magnitudes = [magnitude]
    event.origins = [origin]
    event.creation_info = creation_info.copy()
    # If an MT was done, that's the preferred mag/mech
    event.preferred_magnitude_id = magnitude.resource_id.resource_id
    event.preferred_focal_mechanism_id = focal_mech.resource_id.resource_id
    if evid:
        event.creation_info.version = evid
    event.resource_id = quakeml_rid(event)
    return event


