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
import datetime
from flask import g

class Course(dict):

    def __custom_get__(self, key):
        """For all DotDict.key access, missing or otherwise."""
        return self.get(key, self.get('*', None))


    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


    def __missing__(self, key):
        """For DefaultDotDict[key] access, missing keys."""
        return self.get('*', None)


    def __init__(self, course_id: str, **kwargs):
        """Course implementation."""
        SQL = """
            SELECT      *
            FROM        core.course
            WHERE       course_id = %(course_id)s
        """
        # TODO: Add where clauses
        with g.db.cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                raise ValueError(f"Course ('{course_id}') not found!")


    @property
    def is_ongoing(self):
        now = datetime.datetime.now()
        if self.opens < now:
            if self.closes and self.closes > now:
                return True
        return False


    def __repr__(self) -> str:
        string = ""
        for attr, value in self.__dict__.items():
            string += f"Course.{attr} = {value}\n"
        return string