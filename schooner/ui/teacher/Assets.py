#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Assets.py - Routines and data for material loans
#   2021-08-31  Initial version.
#   2021-09-01  Logic moved to PLPGSQL.
#
#
# Business Logic
#       Draft submission is created when student is handed the materials.
#       Submission.content should contain the asset ID (component kit number).
#       Submission is updated to 'accepted' when the assets are returned.
#
#       -   Assignment.handler must be 'BORROWUI'. This allows this class to
#           filter out other assignments.
#       -   Assignment.retries must be NULL (unlimited). It is possible that
#           the student must return one asset (broken? other reason?) and
#           sign out a new asset. Old is accepted and new submission is created
#           for the new asset. This leaves an audit trail about who used which
#           asset.
#       -   Assignment should be evaluated as "last submission" because only
#           one 'draft' submission can exist for each assignment and evaluating
#           the last will determine if the last loaned asset is returned.
#       -   Recording one submission for each asset will store an audit trail
#           of all the assets that have passed through students hands.
#       -   ASSET LOAN SUBMISSION.CONTENT MUST NOT BE EDITED. If the student
#           keeps the first asset and gets another, existing draft must be
#           closed (accepted) and new created with both IDs in the content.
#
#       If student is loaned multiples of assets ("OK, that was broken,
#       take these two this time so you don't need to come again..."),
#       teachers simply writes both asset IDs into the assignment.content.
#


class Assets(list):
    """Returns enrollee loan data for specified assignment, but ignores returned assets (state = 'accepted')."""

    def __init__(self, cursor, course_id: str, assignment_id: str):
        self.cursor = cursor
        # Does not care about returned loans (state = 'accepted')
        SQL = """
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
                        submission.content AS loan_item_id,
                        submission.submitted AS loan_datetime
            FROM        (
                            SELECT      assignment.*
                            FROM        core.assignment
                            WHERE       assignment.course_id = %(course_id)s
                                        AND
                                        assignment.assignment_id = %(assignment_id)s
                                        AND
                                        assignment.handler = 'ASSETMGR'
                        ) assignment
                        INNER JOIN core.enrollee
                        ON (assignment.course_id = enrollee.course_id)
                        LEFT OUTER JOIN
                        (
                            -- There can only ever be one draft for each assignment at the time
                            SELECT      submission.*
                            FROM        core.submission
                            WHERE       state = 'draft'
                                        AND
                                        course_id = %(course_id)s
                                        AND
                                        assignment_id = %(assignment_id)s
                        ) submission
                        ON (
                            assignment.course_id = submission.course_id
                            AND
                            assignment.assignment_id = submission.assignment_id
                            AND
                            enrollee.uid = submission.uid
                        )
        """
        if cursor.execute(SQL, locals()).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
            )




    def sort(self, key):
        super().sort(key=lambda k : k[key])
        return self




    @staticmethod
    def loan(
        cursor,
        course_id: str,
        assignment_id: str,
        uid: str,
        asset: str
    ) -> int:
        if not cursor.execute(
            "SELECT core.asset_claim(%(course_id)s, %(assignment_id)s, %(uid)s, %(asset)s)",
            locals()
        ).rowcount:
            raise ValueError(
                f"Could not record asset loan for '{item_id}' ('{course_id}', '{assignment_id}', '{uid}')"
            )
        cursor.connection.commit()
        return cursor.fetchone()[0]




    @staticmethod
    def receive(
        cursor,
        submission_id: int,
        feedback: str = None,
        confidential: str = None
    ):
        cursor.execute(
            "CALL core.asset_return(%(submission_id)s, %(feedback)s, %(confidential)s)",
            locals()
        )
        cursor.connection.commit()




    @staticmethod
    def receive_cua(
        cursor,
        course_id: str,
        assignment_id: str,
        uid: str,
        feedback: str = None,
        confidential: str = None
    ):
        """Receive assets back from loan, identified by (course_id, assignment_id, uid) and the knowledge that the submission must be in 'draft' state and for an assignment that has a handler = 'ASSETMGR'."""
        SQL = """
            SELECT      submission.submission_id
            FROM        core.submission
                        INNER JOIN core.assignment
                        ON (
                            submission.course_id = assignment.course_id
                            AND
                            submission.assignment_id = assignment.assignment_id
                        )
            WHERE       submission.course_id = %(course_id)s
                        AND
                        submission.assignment_id = %(assignment_id)s
                        AND
                        submission.uid = %(uid)s
                        AND
                        submission.state = 'draft'
                        AND
                        assignment.handler = 'ASSETMGR'
        """
        if cursor.execute(SQL, locals()).rowcount:
            return Assets.receive(
                cursor,
                cursor.fetchone()[0],
                feedback,
                confidential
            )
        else:
            raise ValueError(
                f"Draft submission ('{course_id}', '{assignment_id}', '{uid}') for ASSETMGR assignment not found!"
            )




    @staticmethod
    def assignments(cursor, active_courses: bool = True):
        """Returns a list of all assignments that deal with material loans."""
        SQL = """
            SELECT      course.code AS course_code,
                        course.name AS course_name,
                        assignment.*
            FROM        core.assignment
                        INNER JOIN core.course
                        ON (assignment.course_id = course.course_id)
            WHERE       handler = 'ASSETMGR'
        """
        if active_courses:
            SQL += """
                AND
                course.course_id IN (
                    SELECT      course_id
                    FROM        core.course
                    WHERE       opens < CURRENT_TIMESTAMP
                                AND
                                (
                                    closes IS NULL
                                    OR
                                    closes > CURRENT_TIMESTAMP
                                )
                )
            """
        cursor.execute(SQL)
        return [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]




# EOF