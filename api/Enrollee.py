#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Enrollee.py
#   2021-08-18  Initial version.
#   2021-08-19  More flexible implementation.
#   
# Relies on global database connection (g.db)
#
from flask import g

class Enrollee(dict):


    def __custom_get__(self, key):
        """For all DotDict.key access, missing or otherwise."""
        return self.get(key, self.get('*', None))


    __getattr__ = __custom_get__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


    def __missing__(self, key):
        """For DefaultDotDict[key] access, missing keys."""
        return self.get('*', None)


    def __init__(self, course_id: str, uid: str) -> None:
        """Queries enrollee data."""
        SQL = """
            SELECT      *
            FROM        core.enrollee
            WHERE       course_id = %(course_id)s
                        AND
                        uid = %(uid)s
            """
        with g.db.cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                raise ValueError(f"Enrollee ('{course_id}', '{uid}') not found!")


    @staticmethod
    def gitcourseids(uid: str, ongoing: bool = True) -> list:
        """Query the list of course-dictinaries in which the student has an *active* enrollment (enrollee.status = 'active'), and which have GitHub registration assignment(s). List is limited to courses that are open, unless parameter 'ongoing' is defined as False"""
        return [c['course_id'] for c in Enrollee.gitcourses(uid, ongoing)]


    @staticmethod
    def gitcourses(uid: str, ongoing: bool = True) -> list:
        """Query the list of course-dictionaries in which the student has an *active* enrollment (enrollee.status = 'active'), and which have GitHub registration assignment. List is limited to courses that are open, unless parameter 'ongoing' is defined as False"""
        if not uid:
            return []
        SQL = """
            SELECT  gitcourse.*
            FROM    core.enrollee
                    INNER JOIN
                    (
                        SELECT      course.*
                        FROM        core.course
                        WHERE       course_id IN (
                                        SELECT      course_id
                                        FROM        core.assignment
                                        WHERE       handler = 'HUBREG'
                                    )
                    ) gitcourse
                    ON (enrollee.course_id = gitcourse.course_id)
            WHERE	enrollee.status = 'active'
                    AND
                    enrollee.uid = %(uid)s
            """
        if ongoing:
            SQL += """
                    AND
                    gitcourse.opens <= CURRENT_TIMESTAMP
                    AND
                    (
                        gitcourse.closes IS NULL
                        OR
                        gitcourse.closes >= CURRENT_TIMESTAMP
                    )
            """
        with g.db.cursor() as c:
            c.execute(SQL, { 'uid' : uid })
        return [dict(zip([key[0] for key in c.description], row)) for row in c]

# EOF