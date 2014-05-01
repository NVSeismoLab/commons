#!/usr/bin/env python
"""
dbrecsec.py script
- Mark Williams (2014)
- Nevada Seismological Laboratory

Needs more doc
"""
import os

import numpy
import obspy.core
from matplotlib import pyplot as plt

import curds2 as dbapi2

T_PRE = 5.
T_POST = 55.


def db2stream(dbname, orid, t_pre=T_PRE, t_post=T_POST):
    """
    Return obspy.Stream of waveforms around p-arrival for a given orid
    """
    DBPROCESS_CMDS = ('process', [('dbopen assoc', 
                      'dbjoin -o arrival', 
                      'dbsubset orid=={0}'.format(orid),
                      'dbsubset iphase=~/P.*/',
                      'dbjoin wfdisc sta chan',
                      'dbsubset arrival.time <= wfdisc.endtime && arrival.time >= wfdisc.time',
                      'dbsort delta',
                      )])
    
    st = obspy.core.Stream()
    dbpath = os.path.abspath(os.path.dirname(dbname))
    with dbapi2.connect(dbname) as conn:
        curs = conn.cursor(CONVERT_NULL=True, row_factory=dbapi2.OrderedDictRow)
        nrecs = curs.execute(*DBPROCESS_CMDS)
        for c in curs:
            fpath = os.path.join(dbpath, c['dir'], c['dfile'])
            t0 = obspy.core.UTCDateTime(c['time']-t_pre)
            t1 = obspy.core.UTCDateTime(c['time']+t_post)
            st += obspy.core.read(fpath, starttime=t0, endtime=t1)
    return st


def plot_stream_recsec(st, time_offset=T_PRE, trace_distance=2):
    """
    Return a figure containing record section plot given an obspy Stream
    """
    bb = 'blue'
    sp = 'black'
    x = 'green'
    color = {'B': bb, 'H': bb, 'E': sp, 'S': sp, 'default':x}
    
    fig = plt.figure(figsize=(16.5, 12.75))
    ax = fig.add_subplot(111)
    ytics = []
    yticlabels = []
    for n, tr in enumerate(st):
        sta = tr.stats.station
        chan = tr.stats.channel
        t = numpy.arange(tr.data.size) / tr.stats.sampling_rate - time_offset
        tr.data = tr.data.astype(numpy.float64)
        tr.data -= tr.data.mean()
        tr.data /= -numpy.amax(numpy.abs(tr.data))
        ypos = trace_distance * n
        tr.data += ypos
        ytics.append(ypos)
        yticlabels.append(' '.join([sta, chan]))
        ax.plot(t, tr.data, linewidth=0.5, color=color.get(chan[0], color['default']))
    ax.set_xlim(t[0],t[-1])
    ax.set_xlabel("Time from P-arrival (s)")
    ax.set_ylim(ypos+trace_distance, 0-trace_distance)
    ax.set_yticks(ytics)
    ax.set_yticklabels(yticlabels, fontsize=20)
    ax.grid(True, axis='x')
    return fig


def main(dbname, orid, filename=None):
    """
    Save a bitmap of waveform plot given dbname/orid
    """
    st = db2stream(dbname, orid)
    if st:
        fig = plot_stream_recsec(st)
        if not filename:
            filename = "waveforms_{0}.png".format(orid)
        fig.savefig(filename)
    else:
        print "No traces in stream"


if __name__=='__main__':
    import sys
    args = sys.argv[1:]
    sys.exit(main(*args))
