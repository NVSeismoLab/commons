# -*- coding: utf-8 -*-
"""
nsl.obspy.patches.geo_interface

This patches the __geo_interface__ into older versions of ObsPy.

"""
from __future__ import unicode_literals
from future.builtins import str  # NOQA


def origin__geo_interface__(self):
    """
    __geo_interface__ method for GeoJSON-type GIS protocol

    :return: dict of valid GeoJSON

    Reference
    ---------
    Python geo_interface specifications:
    https://gist.github.com/sgillies/2217756

    """
    time = None
    update_time = None
    
    coords = [self.longitude, self.latitude]
    if self.depth is not None:
        coords.append(self.depth)
    if isinstance(self.time, UTCDateTime):
        time = str(self.time)
        coords.append(self.time.timestamp)
    
    if self.creation_info and self.creation_info.creation_time is not None:
        update_time = str(self.creation_info.creation_time)

    point = {
        "type": "Point",
        "coordinates": coords,
        "id": str(self.resource_id),
        }
    props = {
        "time": time,
        "updated": update_time,
        }
    return {"type": "Feature", "properties": props, "geometry": point}


def event__geo_interface__(self):
    """
    __geo_interface__ method for GeoJSON-type GIS protocol

    :return: dict of valid GeoJSON

    Reference
    ---------
    Python geo_interface specifications:
    https://gist.github.com/sgillies/2217756

    Schema loosely based on the USGS GeoJSON format
    http://earthquake.usgs.gov/earthquakes/feed/v1.0/GeoJSON.php

    """
    if self.origins:
        o = self.preferred_origin() or self.origins[0]
    else:
        raise ValueError("Event contains no Origins.")

    gj_dict = o.__geo_interface__
    gj_dict['properties'].update(
        {"type": self.event_type,
         "url": str(self.resource_id)})

    if self.magnitudes:
        m = self.preferred_magnitude() or self.magnitudes[0]
        gj_dict['properties'].update(
            {"mag": m.mag,
             "magtype": m.magnitude_type})
    return gj_dict


def station__geo_interface__(self):
    """
    __geo_interface__ method for GeoJSON-type GIS protocol

    :return: dict of valid GeoJSON

    Reference
    ---------
    Python geo_interface specifications:
    https://gist.github.com/sgillies/2217756

    """
    # Convert UTCDateTime objects to str
    times = dict([(a, str(getattr(self, a))) for a in ('start_date',
                 'end_date', 'creation_date', 'termination_date')
                 if getattr(self, a) is not None])

    point = {
        "type": "Point",
        "coordinates": (self.longitude, self.latitude, self.elevation),
        "id": self.code,
        }
    props = {
        "start_date": times.get('start_date'),
        "end_date": times.get('end_date'),
        "creation_date": times.get('creation_date'),
        "termination_date": times.get('termination_date'),
        "description": self.description,
        "alternate_code": self.alternate_code,
        }
    return {"type": "Feature", "properties": props, "geometry": point}


def catalog__geo_interface__(self):
    """
    __geo_interface__ method for GeoJSON-type GIS protocol

    :return: dict of valid GeoJSON

    Reference
    ---------
    Python geo_interface specifications:
    https://gist.github.com/sgillies/2217756
    """
    features = [e.__geo_interface__ for e in self.events]
    return {"type": "FeatureCollection", "features": features}


def network__geo_interface__(self):
    """
    __geo_interface__ method for GeoJSON-type GIS protocol

    :return: dict of valid GeoJSON

    Reference
    ---------
    Python geo_interface specifications:
    https://gist.github.com/sgillies/2217756
    """
    features = [s.__geo_interface__ for s in self.stations]
    return {"type": "FeatureCollection", "features": features}


##############################################################################
# Patch for older ObsPy versions
##############################################################################
from obspy.core.event import Event, Origin, Catalog
from obspy.station import Station, Network

Event.__geo_interface__ = property(event__geo_interface__)
Origin.__geo_interface__ = property(origin__geo_interface__)
Station.__geo_interface__ = property(station__geo_interface__)
Catalog.__geo_interface__ = property(catalog__geo_interface__)
Network.__geo_interface__ = property(network__geo_interface__)

