#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
import time
import psycopg

from util import AppConfig
from util import Lockfile

from schooner.core import Course

if __name__ == '__main__':

    cfg = AppConfig("app.conf", "mailbot")
    """
    with Lockfile(cfg.lockfile) as lock:
        print(Lockfile.file_status(cfg.lockfile))
        time.sleep(3)
        print(Lockfile.file_status(cfg.lockfile))
        time.sleep(3)
    print(Lockfile.file_status(cfg.lockfile))
    """
    with psycopg.connect(f"dbname={cfg.dbname} user={cfg.dbuser}").cursor() as cursor:
        a = Course(cursor)
        for k, v in a.items():
            print(k, v)

