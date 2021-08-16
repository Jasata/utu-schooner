#!/bin/env python3
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
# api/Course.py - Class for course
#
# 2021-08-08    Initial version.
#
# NOTE: Not accepting filename for  to the database because
#       SQLite3 simply creates a new file if one does 
#
import os
import sqlite3


class DataObject():

    def __init__(self, dbfile: str, course_id: str):
        if not os.path.isfile(dbfile):
            raise ValueError(f"Database file '{dbfile}' does not exist!")
        self._dbfile = dbfile
        # 1) 'course' columns as object members
        # 2) self.assignment[] of Assignment Objects

def enrolled_courses(dbfile: str, uid: str):
    """Return a list of """