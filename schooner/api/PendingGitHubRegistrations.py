#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Tuisku Polvinen <tumipo@utu.fi>
#
# PendingGitHubRegistrations.py - List of pending GitHub registrations
#   2021-08-27  Initial version.
#


class PendingGitHubRegistrations(list):
    def __init__(self, cursor):
        SQL = """
            SELECT      course.course_id,
                        course.code AS course_code,
                        course.github_account AS course_account,
                        course.github_accesstoken AS course_accesstoken,
                        submission.submission_id,
                        submission.uid,
                        submission.content AS student_account
            FROM        core.course
                        INNER JOIN (
                            SELECT      course_id,
                                        assignment_id
                            FROM        core.assignment
                            WHERE       handler = 'HUBREG'
                                        AND
                                        deadline > CURRENT_TIMESTAMP
                        ) assignment
                        ON (course.course_id = assignment.course_id)
                        INNER JOIN (
                            SELECT      submission_id,
                                        assignment_id,
                                        course_id,
                                        uid,
                                        content
                            FROM        core.submission
                            WHERE       state = 'draft'
                        ) submission
                        ON (
                            assignment.assignment_id = submission.assignment_id
                            AND
                            assignment.course_id = submission.course_id
                        )
        """
        if cursor.execute(SQL).rowcount:
            super().__init__(
                [dict(zip([key[0] for key in cursor.description], row)) for row in cursor]
            )



# EOF
