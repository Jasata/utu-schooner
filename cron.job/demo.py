#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Very basic demo for a background task.
#
import os
import sys
import time
import logging
import psycopg


# Add parent directory to the search path
# But not as the zero index... because it could be important for 3rd party
# code that may rely on sys.path documentation conformance:
#
#       As initialized upon program startup, the first item of this list,
#       path[0], is the directory containing the script that was used to
#       invoke the Python interpreter.
#
sys.path.insert(
    1,
    os.path.normpath(
        os.path.join(
            os.path.dirname(
                os.path.realpath(
                    os.path.join(
                        os.getcwd(),
                        os.path.expanduser(__file__)
                    )
                )
            ),
            ".." # Parent directory (relative to this script)
        )
    )
)

from schooner.util      import AppConfig
from schooner.util      import Lockfile
from schooner.util      import Timer
from schooner.util      import LogDBHandler

from schooner.db.core   import Course
from schooner.jtd       import JTDSubmission



# Dummy Jinja "parser" (dumps keyword arguments)
def jinja(**kwargs):
    for k, v in kwargs.items():
        print(k, v)
    print("-" * 60)
    print("Enrollee name:", kwargs.pop('enrollee_uid', 'NOT FOUND'))

def dummy_parse(kwargs: dict):
    return jinja(**kwargs)


# Funly ASCII ticker to entertain the masses
def ticker():
    try:
        ticker.count += 1
    except AttributeError:
        ticker.count = 0
    # Did ya know? Cannot have "\" in f-string ... !!
    print(
        "\r{}".format(
            ['\\', '|', '/', '-'][ticker.count % 4]
        ),
        end   = '',
        flush = True
    )



if __name__ == '__main__':

    # Start timer
    runtime = Timer()
    cfg = AppConfig("app.conf", "mailbot")

    #
    # Setup logging
    #
    root = logging.getLogger()
    root.setLevel(cfg.loglevel)
    # STDOUT handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('[%(levelname)s] %(message)s')
    )
    root.addHandler(handler)
    # DB Handler
    handler = LogDBHandler(cfg.database, level = cfg.loglevel)
    root.addHandler(handler)
    # Logging instance with useful name
    log = logging.getLogger(os.path.basename(__file__))

    log.debug("Debug spam")
    log.info("A damn message....")
    log.warning("Warning message")
    log.error("Error message")
    log.exception("Exception")

    print(Lockfile.status_report(cfg.lockfile))
    with Lockfile(cfg.lockfile) as lockfile:
        log.debug(Lockfile.file_status(cfg.lockfile))
        log.debug(Lockfile.status_report(cfg.lockfile))
        time.sleep(3)
        with psycopg.connect(f"dbname={cfg.database}").cursor() as cursor:
            a = Course(cursor)
            for k, v in a.items():
                log.debug(k, v)
            jtd = JTDSubmission(cursor, 2)
            dummy_parse(jtd)
        try:
            log.info("Staring timer (press CTRL-C to quit)")
            while True:
                ticker()
                time.sleep(2)
        except KeyboardInterrupt:
            log.info("\nTerminated with CTRL-C")

    log.debug(str(Lockfile.file_status(cfg.lockfile)))
    log.info(f"Completed in {runtime.report()}")

# EOF
