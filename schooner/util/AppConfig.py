#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# AppConfig.py - Read .conf (with configparser) into a dictionary
#   2021-08-26  Initial version.
#   2021-09-03  Add key-value pairs from DB 'system.config' table,
#               but only if the configuration already defines 'database'.
#
# USAGE
#
#   INTENDED FOR BACKGROUND TASKS - Please do not use in Flash application!
#
#   If section is specified, key-value pairs are loaded from that specific
#   section into the AppConfig dictionary object. If section is not specified,
#   AppConfig dictionary is loaded with all section dictionaries, each
#   containing their key-value pairs.
#
#   If key 'database' now exists, database is queried (IDENT authentication)
#   for 'system.config' table. ONLY KEYS (columns) that are NOT YET SET,
#   are added to the configuration. This way, the configuration files can
#   take precedence.
#
#   Database ('system.config') values are always stored into the "root"
#   dictionary, never under section dictionaries (if the class was constructed
#   without a section argument).
#
#   from schooner.util import AppConfig
#   myCfg = AppConfig("app.conf", "hubbot")
#   allCfg = AppConfig("app.conf")
#
#   printf(f"DATEFORMAT: {myCfg.DATEFORMAT}")
#   for k, v in allCfg.items():
#       if isinstance(v, dict):
#           for k2, v2 in v.items():
#               print(f"{k}.{k2} = {v2}")
#       else:
#           print(f"{k} = {v}")
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
    __getattr__ = dict.__getitem__
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
        #
        # Update with database 'system.config' table
        #
        if 'database' not in self:
            return
        try:
            import psycopg
            with psycopg.connect(f"dbname={self['database']}").cursor() as c:
                if c.execute("SELECT * FROM system.config").rowcount:
                    dbcfg = dict(
                        zip(
                            [key[0] for key in c.description],
                            c.fetchone()
                        )
                    )
                    for k, v in dbcfg.items():
                        # Add only keys that have NOT been set in the config file
                        if k not in self:
                            self[k] = v
                else:
                    # system.config table was empty - this is not allowed!
                    raise ValueError(
                        f"Table query 'system.config' returned empty! There MUST be values!"
                    )
        except:
            # Some smarter exception handling, some day...
            raise


# EOF