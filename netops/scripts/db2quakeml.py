#!/usr/bin/env python
# 
# Script using netops module to generate quakeml
# from Antelope database

import os
from netops.converters import QuakemlConverter as Converter

def db2qml(**kwargs):
    """
    """
    if   'delete' in kwargs and kwargs['delete']:
        product = "delete"
    elif 'mt' in kwargs and kwargs['mt'] is not None:
        product = 'moment'
    elif 'focal_data' in kwargs and kwargs['focal_data']:
        product = 'focal'
    elif 'phase_data' in kwargs and kwargs['phase_data']:
        product = "phase"
    else:
        product = "origin"
    
    database = kwargs.pop('database')
    with Converter(database) as eb:
        eb.build(**kwargs)
        qml_text = eb.quakeml_str()
        qml_file = eb.quakeml_filename(product)
    return {'name': qml_file, 'contents': qml_text}

def write_quakeml(path=None, **kwargs):
    """
    Writes QuakeML to file from a db, all keyword input args
    are passed to EventBuilder.build() function, at NSL this
    is custom, see eventbuilder.EventBuilder or the version
    netops.NSLEventBuilder's 'build' method for details.
   
    Inputs
    ------
    path : str of directory to save file in
    **kwargs
        - passed to EventBuilder.build()
        - depend on implementation
    """
    qml = db2qml(**kwargs)
    if path:
        qml_file = os.path.join(path, qml['name'])
    
    try: 
        with open(qml_file,'w') as qf:
            qf.write(qml['contents'])
    except IOError:
        qml['name'] = ''
    
    return [ qml['name'] ]

# Quickie call for x script (for testing, may go away)
#
# USAGE: ./db2qml.py <database> <orid>
#
if __name__=="__main__":
    import sys
    usage = "Usage: db2quakeml.py <database> <orid>\n   Prints QuakeML to stdout."
    if len(sys.argv) != 3:
        print usage
    else:
        qml = db2qml(database=sys.argv[1], orid=sys.argv[2])
        print qml['contents']
