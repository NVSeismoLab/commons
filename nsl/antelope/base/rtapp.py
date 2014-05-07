# -*- coding: utf-8 -*-
"""
Nevada Seismological Lab - RTApps

NSL NetOps Real-time apps are implemented as scripts in various
languages which filter custom character packets on the ORB to
do non-critical earthquake processing (i.e. NOT preliminary
detection, location, magnitude, etc.) including:

- Event filtering (polygon, verification)
- Event changes (relocations, focal mechanisms)
- Notification (USGS, public channels)
- Website (updates)

This is a simple class for writing RTapps in python.

"""
import sys
import time

from antelope.orb import orbopen

import nsl.common.logging as logging
from nsl import __version__ as nsl_version
from nsl.antelope.pf import get_pf
from nsl.antelope.packets import Pkt

# Default null logger for module
LOG = logging.customLogger(__name__)


def _rt_print(packet_tuple):
    """
    Default example of an rt_app function

    Inputs: packet tuple from orbreap
    ** Prints tuple contents **
    Returns: success code
    """
    print(packet_tuple)
    return 0


class Rtapp(object):
    """
    Base rtapps class

    This is a Base which should be inherited.

    Descendents can define the 'filter_expressions' list
    and MUST define the 'process' method, which is called by 'run'.

    Attributes
    ----------
    orb      : antelope.orb.Orb
    orbname  : str of your orb name
    logger   : logging.Logger instance
    filter_exceptions :  list of strings to check packet source name for

    Methods
    -------
    Rtapp : Constructor - sets orb and function

    filter_packet : Return bool of whether a packet name matches a string

    process : Take a packet tuple and do something

    run     : starts infinite loop of...
              -> orbreaping
              -> checking packet sourcename against 'filter_expressions'
              -> passing packet tuple to 'process' method

    """
    __version__ = 'generic'
    _pffilename = 'rtapp'

    orb = None
    orbname = None
    logger = LOG
    filter_expressions = None

    def __init__(self, orbname=None):
        """
        Constructor for rtapp process stub

        - Sets the name of the orb to be opened at runtime

        Input
        -----
        orbname   : string of orbname server:port

        """
        # Check for None so these could be set at class level
        if orbname is not None:
            self.orbname = orbname

    def _open(self, orbname=None):
        """
        Open the orb associated with the app instance

        """
        if orbname is not None:
            self.orbname = orbname
        self.orb = orbopen(self.orbname)

    def _restart(self):
        """
        Restart the current Rtapp orb

        """
        self.orb.close()
        self._open()

    def _orbcheck(self, packet):
        """
        Check if packet is -1, which means orbserver restarted

        """
        if packet == -1:
            self.logger.warn("Packet -1, restarting ORB...")
            self._restart()

    def filter_packet(self, packet_tuple, expression=None):
        """
        Test packet source name against a given expression

        """
        if expression is None and self.filter_expressions:
            filters = self.filter_expressions
        else:
            if isinstance(expression, str):
                filters = [expression]
            elif isinstance(expression, list):
                filters = expression
            else:
                filters = []
        #
        # Check for matches, reject otherwise, empty list matches any packet
        #
        if filters:
            for f in filters:
                if f in packet_tuple[1]:
                    return True
            return False
        else:
            return True

    def process(self, packettuple):
        """
        Process packet tuple and return integer or packet

        Notes
        -----
        Stub designed to be overwritten by inheriting class
        (this default simply prints the packet)

        """
        return _rt_print(packettuple)
    
    def ship(self, packet):
        """
        Receive packet class and stuff/put it into queue
        """
        (pkttype, pkt, pktsrcname, pkttime) = packet.stuff()
        nbytes = len(bytes(pkt))
        self.orb.put(pktsrcname, pkttime, pkt, nbytes)
        self.logger.info("Wrote packet to orb: {0}".format(pktsrcname))

    def start(self):
        """
        Reap the orb and process the resulting tuple packet

        1) reap a packet tuple off the ORB
        2) check substrings in 'filter_expressions' against packet source name
        3) pass tuple of matching packets to 'process' method
        4) put any packets returned from 'process' into ORB

        """
        # Startup
        self.logger.info("STARTING, nsl.common Version {0}, CONNECTING TO {1}... ".format(
            nsl_version, self.orbname))

        # Open orb connection
        self._open()

        #
        # Main reaping loop
        #
        # Try to keep open and connected, catch and log any errors by the main
        # processing function of the app that make it through.
        #
        while True:
            p = self.orb.reap()
            # Check packets for -1, means the Orb has been restarted
            self._orbcheck(p)
            if self.filter_packet(p):
                try:
                    reply = self.process(p)
                    if isinstance(reply, Pkt):
                        self.ship(reply)
                except Exception as e:
                    reply = 0
                    self.logger.exception(e)
                finally:
                    del reply

    @classmethod
    def main(cls):
        """
        Main function to run as a script
        """
        # Change logger to class name, logging to stderr
        cls.logger = logging.customLogger(cls.__name__, ['stderr'])
        # Prefer command line orb, else see if you have one in a pf
        if len(sys.argv) > 1:
            ORB = sys.argv[1]
        else:
            pf = get_pf(cls._pffilename)
            ORB = pf.get('ORB')
        # Instantiate and run forever
        rtapp = cls(orbname=ORB)
        try:
            rtapp.start()
        except Exception as e:
            rtapp.logger.exception(e)
            rtapp.logger.critical("Uncaught exception, exiting...")
            sys.exit(1)
