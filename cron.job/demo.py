#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import time
import psycopg

from util import AppConfig
from util import Lockfile
from util import Timer

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
    print(Lockfile.status_report(cfg.lockfile))
    with Lockfile(cfg.lockfile) as lockfile:
        print(Lockfile.file_status(cfg.lockfile))
        print(Lockfile.status_report(cfg.lockfile))
        time.sleep(3)
        with psycopg.connect(f"dbname={cfg.database}").cursor() as cursor:
            a = Course(cursor)
            for k, v in a.items():
                print(k, v)
            print("=" * 60)
            jtd = JTDSubmission(cursor, 2)
            #for k, v in jtd.items():
            #    print(k, v)
            dummy_parse(jtd)
        try:
            print("Staring timer (press CTRL-C to quit)")
            while True:
                ticker()
                time.sleep(2)
        except KeyboardInterrupt:
            print("\nTerminated with CTRL-C")

    print(Lockfile.file_status(cfg.lockfile))
    print("Completed in", runtime.report())