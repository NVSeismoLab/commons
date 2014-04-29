# -*- coding: utf-8 -*-
"""
nsl.common.log
"""
import logging


DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


def log_to_stream(logger, stream=None, level=None, formatting=None):
    """
    Add a StreamHandler to a logger (default=stderr)
    """
    if level is None:
        level = DEFAULT_LOG_LEVEL
    if formatting is None:
        formatting = DEFAULT_LOG_FORMAT
    if logger.level < level:
        logger.setLevel(level)
    hnd = logging.StreamHandler(stream=stream)
    hnd.setLevel(level)
    hnd.setFormatter(logging.Formatter(formatting))
    logger.addHandler(hnd)
    return logger


class ModuleLogger(object):
    def __new__(cls, name=None):
        """
        Get a generic logger with a NullHander/disabled
        (Used for logging in API/module, or a base generic logger)
        """
        if name is None:
            name = __name__
        logger = logging.getLogger(name)
        try:
            logger.addHander(logging.NullHandler)
        except:
            logging.raiseExceptions = False
        return logger

    @classmethod
    def to_stream(cls, name=None, stream=None, level=None, formatting=None):
        """
        """
        logger = cls(name)
        return log_to_stream(logger, stream, level, formatting)


class LoggedType(type):
    """
    Metaclass, adds an initialized logger instance
    """
    def __new__(cls, name, bases, dict_):
        dict_['logger'] = ModuleLogger(name)
        return super(LoggedType, cls).__new__(type, name, bases, dict_)
        
