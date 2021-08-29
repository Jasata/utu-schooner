#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import time
import psycopg

from util import AppConfig
from util import Lockfile
from util import Timer
from util import LogDBHandler

from schooner.core  import Course
from templatedata   import JTDSubmission

def jinja(**kwargs):
    for k, v in kwargs.items():
        print(k, v)
    print("-" * 60)
    print("Enrollee name:", kwargs.pop('enrollee_uid', 'NOT FOUND'))

def dummy_parse(kwargs: dict):
    return jinja(**kwargs)

def ticker():
    try:
        ticker.count += 1
    except AttributeError:
        ticker.count = 0
    try:
        print(
            "\r{}".format(
                ['\\', '|', '/', '-'][ticker.count]
            ),
            end   = '',
            flush = True
        )
    except IndexError:
        ticker.count = 0
        print("\r\\", end = '', flush = True)


if __name__ == '__main__':

    # Start timer
    runtime = Timer()
    cfg = AppConfig("app.conf", "mailbot")

    #
    # Setup logging
    #
    import os
    import sys
    import logging
    # Give descriptive name, such as "HUBBOT", "HUBREG", or "MAILBOT" (max 32 chars)
    log = logging.getLogger(os.path.basename(__file__))
    log.setLevel(cfg.loglevel)
    # STDOUT handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('[%(levelname)s] %(message)s')
    )
    log.addHandler(handler)
    # DB Handler
    handler = LogDBHandler(cfg.database, level = cfg.loglevel)
    #handler.setLevel(level=cfg.loglevel)
    log.addHandler(handler)

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
