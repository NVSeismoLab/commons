# -*- coding: utf-8 -*-
"""
nsl.common.logging

Contains python logging module plus some default 
variables, functions and classes for logging.
"""
from logging import *


DEFAULT_LOG_LEVEL = INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def add_logstream(logger, stream=None, level=None, formatting=None):
    """
    Add a StreamHandler to a logger (default=stderr)

    Return stream for access
    """
    if level is None:
        level = DEFAULT_LOG_LEVEL
    if formatting is None:
        formatting = DEFAULT_LOG_FORMAT
    if logger.level < level:
        logger.setLevel(level)
    hnd = StreamHandler(stream=stream)
    hnd.setLevel(level)
    hnd.setFormatter(Formatter(formatting))
    logger.addHandler(hnd)
    return stream


class ModuleLogger(object):
    def __new__(cls, name=None):
        """
        Get a generic logger with a NullHander/disabled
        (Used for logging in API/module, or a base generic logger)
        """
        if name is None:
            name = __name__
        logger = getLogger(name)
        try:
            logger.addHander(NullHandler)
        except:
            raiseExceptions = False
        return logger

    @classmethod
    def to_stream(cls, name=None, stream=None, level=None, formatting=None):
        """
        Simple class constructor to log to a stream
        """
        logger = cls(name)
        st = log_to_stream(logger, stream, level, formatting)
        return logger


class LoggedType(type):
    """
    Metaclass, adds an initialized logger instance
    """
    def __new__(cls, name, bases, dict_):
        dict_['logger'] = ModuleLogger(name)
        return super(LoggedType, cls).__new__(type, name, bases, dict_)
        
