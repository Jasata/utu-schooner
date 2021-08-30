#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# AppConfig.py - Read .conf (with configparser) into a dictionary
#   2021-08-26  Initial version.
#
# USAGE
#   If section is specified, key-value pairs are loaded from that specific
#   section into the AppConfig dictionary object. If section is not specified,
#   AppConfig dictionary is loaded with all section dictionaries, each
#   containing their key-value pairs.
#
#   import schooner
#   myCfg = schooner.AppConfig("app.conf", "hubbot")
#   allCfg = schooner.AppConfig("app.conf")
#
#   printf(f"DATEFORMAT: {myCfg.DATEFORMAT}")
#   printf(f"hubreg.interval: {allCfg.hubreg.interval}")
#
#
#   "What is that [DEFAULT] section anyway?"
#   It is NOT a section - you cannot access it. Instead, key-value pairs
#   placed there are copied to all /actual/ sections... thus, kind of giving
#   them all "default" configuration values.
#
#
import os
import configparser


class DotDict(dict):
    """For DotDict.key access."""
    def __custom_get__(self, key):
        return self[key]
    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class AppConfig(DotDict):
    """Reads a .conf file (with ConfigParser()) into a dictionary."""
    def __init__(self, cfgfile: str, section: str = None) -> None:
        if not os.path.exists(cfgfile):
            raise FileNotFoundError(
                f"Configuration file '{cfgfile}' not found! (cwd: '{os.getcwd()}'"
            )
        cfg = configparser.ConfigParser()
        cfg.optionxform = lambda option: option # preserve case
        cfg.read(cfgfile)
        if section is not None:
            super().__init__(cfg[section])
        else:
            # Load all sections into their own dictionaries
            for sect in cfg.sections():
                self[sect] = DotDict(cfg[sect])

# EOF