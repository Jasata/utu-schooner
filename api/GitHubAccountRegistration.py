#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# GitHubAccountRegistration.py - GitHub account registration data
#   2021-08-18  Initial version.
#   2021-08-19  Query updated for enrollee table changes.
#   
#
# Class creates a dot-notation access dictionary, containing the
# keys from the query's SELECT list.
#
import datetime
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
        """Load object with registration data."""
        SQL = """
            SELECT      course.course_id,
                        course.opens AS course_opens,
                        course.closes AS course_closes,
                        enrollee.uid,
                        CASE
                            WHEN enrollee.studentid IS NULL THEN 'n'
                            ELSE 'y'
                        END AS has_enrolled,
                        CASE
                            WHEN submission.assignment_id IS NULL THEN 'n'
                            ELSE 'y'
                        END AS has_submission,
                        enrollee.github_account,
                        enrollee.github_repository,
                        assignment.assignment_id,
                        submission.content,
                        submission.state,
                        submission.evaluator,
                        submission.score,
                        submission.created,
                        submission.modified
            FROM        (
                            SELECT      *
                            FROM        enrollee
                            WHERE       uid = %(uid)s
                                        AND
                                        course_id = %(course_id)s
                        ) enrollee RIGHT OUTER JOIN course
                        ON (enrollee.course_id = course.course_id)
                        LEFT OUTER JOIN (
                            -- Unique index guarantees that there can be only one (or none) 'HUBREG' assignments
                            SELECT      assignment.*
                            FROM        assignment
                            WHERE       handler = 'HUBREG'
                        ) assignment
                        ON (course.course_id = assignment.course_id)
                        LEFT OUTER JOIN (
                            SELECT      *
                            FROM        submission
                            WHERE       uid = %(uid)s
                        ) submission
                        ON (
                            assignment.course_id = submission.course_id
                            AND
                            assignment.assignment_id = submission.assignment_id
                        )
            WHERE		course.course_id = %(course_id)s
        """
        with g.db.cursor() as c:
            if c.execute(SQL, locals()).rowcount:
                self.update(dict(zip([key[0] for key in c.description], c.fetchone())))
            else:
                raise ValueError(f"Course ('{course_id}') not found!")
                #self.update(dict(zip([key[0] for key in c.description], [None] * len(c.description))))
        # Other exceptional reasons
        if not self.assignment_id:
            raise ValueError(f"Course ('{course_id}') does not have GitHub account registration!")
        if not self.uid:
            raise ValueError(f"Student ('{uid}') is not enrolled in course ('{course_id}')!")


    @property
    def is_enrolled(self) -> bool:
        """True, if student has been enrolled to the course."""
        return True if self.has_enrolled == 'y' else False

    @property
    def has_submission(self) -> bool:
        """True, if student has HUBREG submission."""
        return True if self.has_submission else False

    @property
    def is_open(self):
        """True unless registration-assignment deadline has been passed?"""
        return True if self.deadline > datetime.datetime.now() else False

# EOF