#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Import configuration key-values from .conf file to global scope.
# Suitable for simple scripts that need a common configuration.
#
# + Simple and short.
# - If the .conf file omits the key, it's a NameError exception.
# - Lint and other checkers will complain about undefined variables.
# - configparser is getting deprecated along with distutils in Python 3.12???
# - configparser has an idiotic escape char '%'...
#
# app.conf example:
"""
[DEFAULT]
# Double % signs because of the very unfortunate use as an escape char

[Application]
DATABASE = /tmp/application.sqlite3
DATEFORMAT = %%Y-%%m-%%d
"""
import os

CONFIG_FILE = "app.conf"

def read_config_file(cfgfile: str):
    """Reads (with ConfigParser()) '[Application]' and creates global variables. Argument 'cfgfile' has to be a filename only (not path + file) and the file must exist in the same directory as this script."""
    cfgfile = os.path.join(
        os.path.split(os.path.realpath(__file__))[0],
        cfgfile
    )
    if not os.path.exists(cfgfile):
        raise FileNotFoundError(f"Configuration file '{cfgfile}' not found!")
    import configparser
    cfg = configparser.ConfigParser()
    cfg.optionxform = lambda option: option # preserve case
    cfg.read(cfgfile)
    for k, v in cfg.items('Application'):
        globals()[k] = v


if __name__ == '__main__':

    try:
        print(f"Reading site configuration '{CONFIG_FILE}'")
        read_config_file(CONFIG_FILE)
    except Exception as ex:
        print(f"Error reading site configuration '{CONFIG_FILE}'")
        print(str(ex))
        os._exit(-1)

    # Demonstrate example key-values
    import time
    print(f"Today is {time.strftime(DATEFORMAT, time.gmtime())}")
    print(
        f"Database '{DATABASE}' "
        f"{('does not exist', 'exists')[os.path.exists(DATABASE)]}"
    )
