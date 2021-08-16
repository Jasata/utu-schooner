#!/bin/env python3
#
# Schooner - Simple Course Management System
# admin.insert.py / Add script owner as an Admin
# University of Turku / Faculty of Technology / Department of Computing
# Jani Tammi <jasata@utu.fi>
#
#  2021-08-13  Initial version.
#
# NOTE: Using Psycopg 3 (dev2) 2021-08-13
#
import os
import pwd
import syslog
import psycopg

# Owner of this file - the user who pulled/cloned this repository
GITUSER  = pwd.getpwuid(os.stat(__file__).st_uid).pw_name

# This syntax doesn't work with psycopg3.. ? To-be-investigated...
#with psycopg.connect(dbname="schooner" user="postgres") as conn:
with psycopg.connect("dbname=schooner user=postgres") as conn:

    with conn.cursor() as cur:

        try:
            cur.execute(
                "INSERT INTO admin (uid) VALUES (%(uid)s)",
                { "uid" : GITUSER }
            )

        except psycopg.Error as e:
            syslog.syslog(
                "Database error: " + e + ", SQL: " + cur.query
            )
            os._exit(1)
        else:
            syslog.syslog(
                f"{GITUSER} added as an Admin"
            )
