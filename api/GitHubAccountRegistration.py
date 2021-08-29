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
    """GitHub account registration object. Typical HUBREG -handler assignment (Github account registration assignment) accepts unlimited number of submissions (allowing the student to change the account and/or repository, for whatever reason). For application point-of-view, the newest submission for this assignment is what is interesting, and older submissions are disregarded."""


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
                        course.code AS course_code,
                        course.name AS course_name,
                        course.opens AS course_opens,
                        course.closes AS course_closes,
                        enrollee.uid,
                        CASE
                            WHEN submission.assignment_id IS NULL THEN 'n'
                            ELSE 'y'
                        END AS github_account_submitted,
                        CASE
                            WHEN assignment.deadline >= CURRENT_DATE THEN 'y'
                            ELSE 'n'
                        END AS github_registration_open,
                        assignment.assignment_id,
                        assignment.deadline AS deadline,
                        enrollee.github_account,
                        enrollee.github_repository,
                        submission.content AS submission_content,
                        submission.state AS submission_state,
                        submission.evaluator AS submission_evaluator,
                        submission.score AS submission_score,
                        submission.submitted AS submission_created,
                        submission.accepted AS submission_modified
            FROM        (
                            SELECT      *
                            FROM        core.enrollee
                            WHERE       uid = %(uid)s
                                        AND
                                        course_id = %(course_id)s
                        ) enrollee RIGHT OUTER JOIN core.course
                        ON (enrollee.course_id = course.course_id)
                        LEFT OUTER JOIN (
                            -- Unique index guarantees that there can be
                            -- only one (or none) 'HUBREG' assignments
                            SELECT      assignment.*
                            FROM        core.assignment
                            WHERE       handler = 'HUBREG'
                        ) assignment
                        ON (course.course_id = assignment.course_id)
                        LEFT OUTER JOIN (
                            SELECT      *
                            FROM        core.submission
                            WHERE       submitted = (
                                            SELECT      MAX(submitted)
                                            FROM        core.submission s
                                            WHERE       s.uid = %(uid)s
                                                        AND
                                                        s.course_id = submission.course_id
                                                        AND
                                                        s.assignment_id = submission.assignment_id
                                        )
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
        return True if self.deadline > datetime.date.today() else False


    def submit(self, account_name: str):
        """Updates existing 'draft' state submission, or if one doesn't exist, inserts a new one."""
        # First try to update 'draft' submission, if no affected rows, then insert
        UPDATE = """
            UPDATE      core.submission
            SET         content         = %(account_name)s
            WHERE       uid             = %(uid)s
                        AND
                        assignment_id   = %(assignment_id)s
                        AND
                        course_id       = %(course_id)s
                        AND
                        state           = 'draft'
        """
        INSERT = """
            INSERT INTO core.submission (course_id, assignment_id, uid, content)
            VALUES (%(course_id)s, %(assignment_id)s,  %(uid)s, %(account_name)s)
        """
        args = {
            **{k: self[k] for k in self.keys() & ('course_id', 'assignment_id', 'uid')},
            'account_name' : account_name
        }
        # {**self, **locals()}
        with g.db.cursor() as c:
            if not c.execute(UPDATE, args).rowcount:
                if not c.execute(INSERT, args).rowcount:
                    raise ValueError(
                        """Failed to create GitHub account registration submission! course_id: {course_id}, assignment_id: {assignmen_id}, uid: {uid}""".format(self)
                    )
                else:
                    g.db.commit()
                    return "inserted something!"
            else:
                g.db.commit()
                return "Updated ..something!"
        return args





if __name__ == '__main__':

    # MUST execute as local user 'schooner'
    import psycopg
    from flask import Flask
    app = Flask(__name__)
    with app.app_context():
        if not hasattr(g, 'db'):
            g.db = psycopg.connect("dbname=schooner user=schooner")
        r = GitHubAccountRegistration('DTE20068-3002', 'lazy')
        print(r)

# EOF
