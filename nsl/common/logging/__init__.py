# -*- coding: utf-8 -*-
"""
nsl.common.logging

Contains python logging module plus some default 
variables, functions and classes for logging.
"""
from logging import *
try:
    from logging.config import dictConfig
except ImportError:
    def dictConfig(config):
        """
        Backward compatible incomplete replacement for logging.config.dictConfig
        (for Python 2.6)
        """
        # Works for the current settings in customConfig only!!!
        # -- For any changes compatibility MUST be added to this as well
        # TODO: implement streams using 'ext://' url notation
        for logname in config.get('loggers', []):
            logconfig = config['loggers'][logname]
            logger = getLogger(logname)
            logger.setLevel(logconfig.get('level',0))
            logger.handlers = []
            for hndname in logconfig.get('handlers', []):
                hndconfig = config['handlers'][hndname]
                classname = hndconfig.get('class').strip('logging.')
                formatname = hndconfig.get('formatter')
                hndlevel = hndconfig.get('level', 0)
                class_ = globals()[classname]
                hnd = class_()
                hnd.setLevel(hndlevel)
                if formatname:
                    fmtconfig = config['formatters'][formatname]
                    formatter = Formatter(fmtconfig.get('format'))
                    hnd.setFormatter(formatter)
                logger.handlers.append(hnd)


DEFAULT_LOG_LEVEL = INFO
#DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_LOG_FORMAT = '%(asctime)s [%(levelname)s]: %(message)s'


def customConfig(name='root', handlers=['null'], level=DEFAULT_LOG_LEVEL):
    """
    Return a dict for logging.config.dictConfig
    
    name: str of logger name to add
    handlers: list of: 'null' -> NullHandler
                       'stderr' -> StreamHandler:stderr
    """
    return {
        'version': 1,
        'formatters': { 
            'default': {
                'format': DEFAULT_LOG_FORMAT
                },
            },
        'handlers' : { 
            'null': {
                'class': 'logging.NullHandler'
                },
            'stderr' : {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
                'level': level,
                },
            },
        'loggers': {
            name : {
                'level': level,
                'handlers': handlers,
                },
            },
        'disable_existing_loggers': False,
        }


def customLogger(name='root', handlers=['null'], level=DEFAULT_LOG_LEVEL):
    """
    Return custom logger built with customConfig function
    """
    dictConfig(customConfig(name, handlers, level))
    return getLogger(name)


class LoggedType(type):
    """
    Metaclass, adds an initialized logger instance
    """
    def __new__(cls, name, bases, dict_):
        dict_['logger'] = customLogger(name)
        return super(LoggedType, cls).__new__(type, name, bases, dict_)
        

#--- Python 2.6 compat -----------------------------------------------#
class NullLogger(object):
    def __new__(cls, name=None):
        """
        Get a generic logger with a NullHander/disabled
        (Used for logging in API/module, or a base generic logger)
        """
        logger = getLogger(name)
        if not logger.handlers:
            try:
                logger.addHander(NullHandler)
            except:
                raiseExceptions = False
        return logger
#---------------------------------------------------------------------#
