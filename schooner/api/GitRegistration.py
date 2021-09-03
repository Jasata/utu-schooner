#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# GitRegistration.py - Data dictionary class for Git registration
#   2021-09-03  Initial version.
#
#
from schooner.db.email import Template
from schooner.jtd      import JTDSubmission


class GitRegistration(dict):

    def __init__(self, cursor, course_id: str, uid: str) -> None:
        """Load object with registration data."""
        self.cursor = cursor
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
            WHERE       course.course_id = %(course_id)s
        """
        if cursor.execute(SQL, locals()).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )
        else:
            raise ValueError(f"Course ('{course_id}') not found!")

        # Other exceptional reasons
        if not self['assignment_id']:
            raise ValueError(
                f"Course ('{course_id}') does not have GitHub account registration assignment!"
            )
        if not self['uid']:
            raise ValueError(
                f"Student ('{uid}') is not enrolled in course ('{course_id}')!"
            )




    def register_account(self, account_name: str):
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
        if not self.cursor.execute(UPDATE, args).rowcount:
            if not self.cursor.execute(INSERT, args).rowcount:
                raise Exception(
                    """Failed to create GitHub account registration submission! course_id: {course_id}, assignment_id: {assignmen_id}, uid: {uid}""".format(self)
                )
        self.cursor.connection.commit()




    @staticmethod
    def register_repository(cursor, submission_id: int, repository: str) -> None:
        cursor.execute(
            "CALL core.register_github(%(submission_id)s, %(repository)s)",
            locals()
        )
        #
        # Send registration message
        #
        template    = Template(cursor, 'HUBREG')
        data        = JTDSubmission(cursor, submission_id)
        template.parse_and_queue(
            data['course_id'],
            data['enrollee_uid'],
            **data
        )
        cursor.connection.commit()


# EOF