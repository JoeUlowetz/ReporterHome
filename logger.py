#!/usr/bin/python3
# logger.py
# added 2021.06.11 Joe Ulowetz, for logging on RPi for RPi-CameraServer
# 2021.09.14 Joe Ulowetz: moved log file location to: /home/pi/ImpossibleObjects/logfiles/

import logging
from logging.handlers import TimedRotatingFileHandler
from ioutils.logfiles import log_name_to_level
import json
import os
import inspect

global logger
logger = None


def set_logger():
    """Set the logging level
    sDebug (str): the logging level - WARNING/FALSE, DEBUG/TRUE, INFO, ERROR, or CRITICAL
    """

    """
    log_path = '/home/pi/ImpossibleObjects/logfiles'    # LOGFILE_BASE
    camera_short_name = camera[:-6]     # just Platen or Outfeed or ...
    date_string = date.today().strftime('%Y_%m_%d')
    filename = os.path.join(log_path, f'{camera_short_name}.{date_string}.log')
    path, base = os.path.split(filename)
    if path:
        if not os.path.exists(path):
            os.makedirs(path)
    log_config(debug_level, filename)
    """

    log_file_location = '/home/pi/ImpossibleObjects/logfiles/logfile.log'
    path, base = os.path.split(log_file_location)
    if path:
        if not os.path.exists(path):
            os.makedirs(path)

    # format the log entries
    fmt = "%(levelname)s; %(asctime)s; %(message)s"     # this is what SWZP uses
    # Old: fmt = '%(asctime)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)

    handler = TimedRotatingFileHandler(log_file_location, when='midnight', backupCount=90)
    handler.setFormatter(formatter)
    global logger
    logger = logging.getLogger('CameraServer')
    if logger.hasHandlers():
        logger.handlers.clear()     # I'm not sure why it already has a handler at this point, but this fixes it.
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


def log_event(level, tag: str, **kwargs) -> None:
    """
        Add a log event to the logs.

    :param level: level for the event -- see below for details.
    :param tag: the tag for the event
    :param kwargs: keyword value pairs for the data portion of the event
    :return: None

    valid logging levels are same as the logging module -- Either an int (logging.DEBUG, logging.INFO, logging.WARNING,
    logging.ERROR, logging.CRITICAL) or a string ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

    events have the format:
        level; timestamp; tag; data

    where data is of the form:
        key1=value1, key2=value2, ....

    for example:

        log_event("DEBUG", "SENSOR_VALUES", sensor_a=1230.41, sensor_b=65)

    --or--

    data = { 'sensor_a': 1230.41, 'sensor_b': 65 }
        log_event("DEBUG", "SENSOR_VALUES",**data)

    """
    # There might be better ways to do this, but logfiles.log_event() isn't working
    # with how I initialized the logger here, so make my own version of the function.
    # Yes, this is copied straight from logfiles.py, and then simplified.

    # flatten kwargs in case the user calls with something like data={"a": 1} instead of **data
    use_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, dict):  # flatten the nested dict
            use_kwargs.update(**v)
        else:
            use_kwargs[k] = v

    msg = f'{tag};'
    if len(use_kwargs) > 0:
        try:
            msg += f' {json.dumps(use_kwargs)}'
        except TypeError as e:
            print("Error: trying to pass a network argument that is not JSON serializable:")
            print(use_kwargs)
            caller = inspect.currentframe().f_back.f_code.co_name
            logging.critical(f'log_message (called from {caller}): - json TypeError - {e}')

    log_level = log_name_to_level(level)

    if log_level >= logging.CRITICAL:
        logger.critical(msg)
    elif log_level >= logging.ERROR:
        logger.error(msg)
    elif log_level >= logging.WARNING:
        logger.warning(msg)
    elif log_level >= logging.INFO:
        logger.info(msg)
    elif log_level >= logging.DEBUG:
        logger.debug(msg)
    else:  # MAXIMUM
        logger.log(msg)

