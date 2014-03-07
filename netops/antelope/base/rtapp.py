#
# Mark's port of netops rtapps to python
#
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
import datetime
import logging
from antelope.orb import Orb
from netops.antelope.util import __antelopeversion__

if '5.3' in __antelopeversion__:
    from antelope.Pkt import Packet as Pkt
else:
    from antelope.Pkt import Pkt

def _rt_print(packet_tuple):
    '''
    Default example of an rt_app function
    
    Inputs: packet tuple from orbreap
    ** Prints tuple contents **
    Returns: success code
    '''
    print packet_tuple
    return 0


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
    orb     = None
    orbname = None
    logger  = None

    filter_expressions = None
    
    def __init__(self, orbname=None, log_level='DEBUG'):
        """
        Constructor for rtapp process stub
        
        - Sets the name of the orb to be opened at runtime
        - Sets up the logger using 'logging' (default STDERR)

        Input
        -----
        orbname   : string of orbname server:port
        log_level : string of logging level ('DEBUG')
        
        """
        self.orbname = orbname
        self._init_log(level=log_level)
    
    def _init_log(self, level='DEBUG'):
        """
        Setup a logger.
        
        Inputs
        ------
        level : string of valid logging level ('DEBUG')
        
        Generates a logging.Logger available at the 'logger' attribute
        -> contains one handler to log to stderr stream
        -> Stream handler logging level specified by 'level'

        """
        # create logger
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(logging.DEBUG)
        # create console handler and set level
        ch = logging.StreamHandler() # default stream=sys.stderr
        lvl = getattr(logging, level.upper())
        ch.setLevel(lvl)
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # add formatter to ch
        ch.setFormatter(formatter)
        # add ch to logger
        logger.addHandler(ch)
        self.logger = logger

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
                filters = expresssion
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

    def process(self, packet):
        """
        Process packet tuple and return integer or packet
        
        Notes
        -----
        Stub designed to be overwritten by inheriting class
        (this default simply prints the packet)
        
        """
        return _rt_print(packet)

    def run(self):
        """
        Reap the orb and process the resulting tuple packet

        1) reap a packet tuple off the ORB
        2) check substrings in 'filter_expressions' against packet source name
        3) pass tuple of matching packets to 'process' method
        4) ***NOT IMPLEMENTED*** put any packets returned from 'process' into ORB
        
        """
        # Startup
        self.logger.info("STARTING RTAPP, CONNECTING TO {orb}... ".format(orb=self.orbname))
        
        # Open orb connection
        self._open()
        self.logger.info("Connected.")
        
        #
        # Main reaping loop
        #
        # Try to keep open and connected, catch and log any errors by the main
        # processing function of the app that make it through.
        #
        while True:
            p = self.orb.reap()
            # Check packets for -1, means the Orb has been restarted without you.
            self._orbcheck(p)
            
            time.sleep(0.5) # wait half a sec for a KeyboardInterrupt
            if self.filter_packet(p):
                try:
                    rc = self.process(p)
                except Exception as e:
                    rc = 0 
                    self.logger.exception(e)
                #todo: check if function returns a packet and try to put it into the orb
                if isinstance(rc, Pkt):
                    (pkttype, pkt, pktsrcname,pktime) = rc.stuff()
                    nbytes = len(bytes(pkt))
                    #try:
                    #    self.orb.put(pktsrcname, pkttime, pkt, nbytes)
                    #except Exception as e:
                    #    self.logger.exception(e)
            
            time.sleep(0.5)



