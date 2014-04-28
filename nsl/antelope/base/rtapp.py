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
#import datetime
import logging
from antelope.orb import Orb
from nsl.antelope.pf import get_pf
from nsl.antelope.packets import Pkt

# Set up logger for debug and real-time
LOG = logging.getLogger(__name__)
DEFAULT_LOG_LEVEL = logging.DEBUG
try:
    LOG.addHandler(logging.NullHandler())
except:
    logging.raiseExceptions = False


def _rt_print(packet_tuple):
    '''
    Default example of an rt_app function

    Inputs: packet tuple from orbreap
    ** Prints tuple contents **
    Returns: success code
    '''
    print(packet_tuple)
    return 0


def _add_stderr_log(logger=LOG, level=DEFAULT_LOG_LEVEL):
    """
    Setup a STDERR Handler for a given Logger.

    Inputs
    ------
    logger : logging.Logger instance
    level : string of valid logging level ('DEBUG')

    -> contains one handler to log to stderr stream
    -> Stream handler logging level specified by 'level'

    """
    # create console handler and set level
    ch = logging.StreamHandler()  # default stream=sys.stderr
    ch.setLevel(level)
    logfmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(logfmt)
    # add formatter to ch
    ch.setFormatter(formatter)
    # add ch to logger
    logger.addHandler(ch)


class Rtapp(object):
    '''
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

    '''
    __version__ = '1.0.0-generic'
    _pffilename = 'rtapp'
    orb = None
    orbname = None
    logger = LOG
    enable_log = False
    log_level = DEFAULT_LOG_LEVEL

    filter_expressions = None

    @classmethod
    def enable_logging(cls, level=logging.DEBUG):
        cls.logger.setLevel(level)

    @classmethod
    def disable_logging(cls):
        cls.logger.setLevel(logging.NOTSET)

    @classmethod
    def log_to_stderr(cls, level=None):
        """
        Convenience method to add a handler to log to STDERR.

        NOTE
        ====
        Logging must be enabled in constructor for messages to get sent!

        """
        if level is None:
            level = cls.log_level
        _add_stderr_log(logger=cls.logger, level=level)

    def __init__(self, orbname=None, enable_log=False):
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
        if enable_log:
            self.enable_logging()

    def _open(self, orbname=None):
        """
        Open the orb associated with the app instance

        """
        if orbname is not None:
            self.orbname = orbname
        self.orb = Orb(self.orbname)

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

    def run(self, enable_log=None):
        """
        Reap the orb and process the resulting tuple packet

        1) reap a packet tuple off the ORB
        2) check substrings in 'filter_expressions' against packet source name
        3) pass tuple of matching packets to 'process' method
        4) put any packets returned from 'process' into ORB

        """
        if enable_log is True:
            # Turn on logging
            # Must add a handler to see these messages!!!
            self.enable_logging()
        elif enable_log is False:
            # Explicitly turn off
            self.disable_logging()
        else:
            # Keep whatever logging was previously set up.
            pass

        # Startup
        self.logger.info("STARTING {0}, CONNECTING TO {1}... ".format(
            self.__class__.__name__, self.orbname))

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

            time.sleep(0.5)  # wait half a sec for a KeyboardInterrupt
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
        if len(sys.argv) > 1:
            ORB = sys.argv[1]
        else:
            pf = get_pf(cls._pffilename)
            ORB = pf.get('ORB')

        rt = cls(orbname=ORB, enable_log=True)
        rt.log_to_stderr()
        try:
            rt.run()
        except Exception as e:
            rt.logger.exception(e)
            rt.logger.critical("Uncaught exception, exiting...")
            sys.exit(1)
