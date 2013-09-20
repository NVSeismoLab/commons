# -*- coding: utf-8 -*-
"""
This is just a config file to define the content of character packets
based on subcode.

"""
subcode_content = {
    'event_new'          : ('evid','orid','mag','time','srcdb','snapdb'),
    'event_pre'          : ('evid','orid','mag','time','srcdb','snapdb'),
    'event_delete'       : ('evid','orid'),
    'event_old'          : ('evid','orid'),
    'event_hypo'         : ('evid','orid','mag','time','srcdb','snapdb'),
    'event_mark_reviewed'   : (None,),
    'db2shakemap_pre'       : (None,),
    'rttimer_sync'          : ('interval',),
    'rtweb_delete'          : (None,),
    'rtweb_new'             : (None,),
    'rtweb_new-external'    : (None,),
    'rtweb_pre'             : (None,),
    'rtweb_pre-external'    : (None,),
    'rtweb_sync'            : ('time',),
    'reporter_hypo'         : (None,),
    'reporter_hypo-external': (None,),
    'reporter_new'          : (None,),
    'reporter_new-external' : (None,),
    'reporter_pre'          : (None,),
    'reporter_pre-external' : (None,),
    'reporter_delete'       : ('evid','orid'),
    'rt_hazus_pre'          : (None,),
    'rtfocalmech_pre'       : (None,),
    'mw_new'                : (None,),
    'mw_pre'                : (None,),
    'mw_publish'            : ('mt',),
}

# Map these to non-string types when unpickling to a dict
#
int_types   = ('evid','orid','interval')
float_types = ('mag', 'time')

