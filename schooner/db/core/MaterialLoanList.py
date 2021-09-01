#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# MaterialLoanList.py - List of data dictionaries for material loans
#   2021-08-31  Initial version.
#

class MaterialLoanList(list):

    def __init__(self, cursor, course_id: str):
        # Does not care about returned loans (state = 'accepted')
        self.SQL = """
            SELECT      assignment.course_id,
                        assignment.assignment_id,
                        assignment.name AS assignment_name,
                        assignment.description AS assignment_description,
                        assignment.deadline,
                        enrollee.uid,
                        enrollee.lastname,
                        enrollee.firstname,
                        enrollee.studentid,
                        CASE
                            WHEN submission.submission_id IS NOT NULL THEN 'y'
                            ELSE 'n'
                        END AS already_signed,
                        submission.content AS load_item_id,
                        submission.submitted AS loan_datetime
            FROM        core.enrollee
                        INNER JOIN core.assignment
                        ON (enrollee.course_id = assignment.course_id)
                        LEFT OUTER JOIN
                        (
                            -- There can only ever be one draft at the time
                            SELECT		submission.*
                            FROM		core.submission
                            WHERE		state = 'draft'
                        ) submission
                        ON (
                            assignment.course_id = submission.course_id
                            AND
                            assignment.assignment_id = submission.assignment_id
                        )
            WHERE       assignment.handler = 'BORROWUI'
                        AND
                        assignment.course_id = %(course_id)s
        """
        if cursor.execute(self.SQL, locals()).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
            )


    def sort(self, key):
        super().sort(key=lambda k : k[key])
        return self



# EOF