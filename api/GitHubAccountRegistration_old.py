#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# GitHubAccountRegistration.py - Handle GitHub account registration
#   2021-08-18  Initial version.
#   
#
# Class creates a dot-notation access dictionary, containing:
#   - .enrollee_github      Value from enrollee.github.
#   - .course_opens         Value from course.opens
#   - .course_closes        Value from course.closes
#   - .*                    Same keys as column names in submission table
#
from flask import g


class GitHubAccountRegistration(dict):
    """GitHub account registration data object. Dot-notation access dict with default key '*'. Returns value for key '*' for missing missing keys, or None if '*' value has not been set."""


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
        """If the user is authenticated, and course_id is specified, queries the data."""
        SQL = """
            SELECT      github
            FROM        enrollee
            WHERE       course_id = %(course_id)s
                        AND
                        uid = %(uid)s
        """
        with g.db.cursor() as c:
            if not c.execute(SQL, locals()).rowcount:
                raise ValueError(f"Enrollee ('{course_id}', '{uid}') not found!")
            self.enrollee_github = c.fetchone()[0]
        # Query course.opens and course.closes
        SQL = """
            SELECT      course.opens,
                        course.closes
            FROM        course
            WHERE       course.course_id = %(course_id)s
        """
        with g.db.cursor() as c:
            if not c.execute(SQL, locals()).rowcount:
                raise ValueError(f"Course ('{course_id}' not found!)")
            (self.course_opens, self.course_closes) = c.fetchone()
        # Query the related submission.
        SQL = """
            SELECT      submission.*
            FROM        submission
            WHERE       course_id = %(course_id)s
                        AND
                        uid = %(uid)s
                        AND
                        assignment_id = (
                            -- Unique index guarantees that there can only be
                            -- zero or one 'HUBREG' assignments per course.
                            SELECT      assignment_id
                            FROM        assignment
                            WHERE       course_id = %(course_id)s
                                        AND
                                        handler = 'HUBREG'
                        )
        """
        with g.db.cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                self.update(dict(zip([key[0] for key in c.description], [None] * len(c.description))))


# EOF