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
    pass

DEFAULT_LOG_LEVEL = INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def customConfig(name='root', handlers=['null'], level=DEFAULT_LOG_LEVEL):
    """
    Return a dict for loggning.config.dictConfig
    
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


class LoggedType(type):
    """
    Metaclass, adds an initialized logger instance
    """
    def __new__(cls, name, bases, dict_):
        dict_['logger'] = NullLogger(name)
        return super(LoggedType, cls).__new__(type, name, bases, dict_)
        
