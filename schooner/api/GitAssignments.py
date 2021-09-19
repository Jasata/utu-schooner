#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# GitAssignments.py - Data dictionary class for assistant.assistant
#   2021-09-07  Initial version.
#   2021-09-18  Assignment WHERE clause modified for NULL deadline.
#               Fixed date range conditions
#
#
# Enrollees for whom a repository fetch CAN be made for are those that must NOT have...
#   1)  A 'draft' submission (pending evaluation)
#   2)  'accepted' must not exist (because that means "done")
#   3)  SUM() must be < .retries + 1# Consider this more "proper" data object than "Assistant"
#
#
# NOTE: Used only by gitbot.py and hubbot.py (2021-09-18)
#


class GitAssignments(list):

    # HUBBOT assignments which have passed their deadlines by one day
    # ...OR have a soft deadline and have not passed that more than one day
    # ("one day" because all fetches take AFTER midnight, on the next day)
    SQL = """
        SELECT      assignment.assignment_id,
                    assignment.course_id,
                    assignment.retries,
                    assignment.deadline,
                    core.submission_last_retrieval_date(assignment.deadline, assignment.latepenalty) AS last_retrieval_date
        FROM        core.assignment
        WHERE       assignment.handler = 'HUBBOT'
                    AND
                    (
                        deadline IS NULL
                        OR
                        (
                            deadline < CURRENT_DATE
                            AND
                            core.submission_last_retrieval_date(assignment.deadline, assignment.latepenalty) >= CURRENT_DATE
                        )
                    )
    """


    def __init__(self, cursor):
        self.cursor = cursor
        cursor.execute(GitAssignments.SQL)
        super().__init__(
            [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
        )


#    def submissions(self, course_id: str, assignment_id: str) -> list:
    def submissions(self, **kwargs) -> list:
        """Returns a list of submissions for given assignment."""
        SQL = """
            SELECT      enrollee.uid,
                        enrollee.lastname,
                        enrollee.firstname,
                        enrollee.github_account,
                        enrollee.github_repository,
                        enrollee.status,
                        submission.submission_id AS draft_submission_id,
                        accepted.submission_id AS accepted_submission_id,
                        coalesce(total_submissions.n_submissions, 0) AS n_submissions
            FROM        core.enrollee
                        LEFT OUTER JOIN core.submission
                        ON (
                            enrollee.course_id = submission.course_id
                            AND
                            enrollee.uid = submission.uid
                            AND
                            submission.assignment_id = %(assignment_id)s
                            AND
                            submission.state = 'draft'
                        )
                        LEFT OUTER JOIN (
                            SELECT      uid,
                                        course_id,
                                        assignment_id,
                                        COUNT(submission_id) AS n_submissions
                            FROM        core.submission
                            GROUP BY    uid,
                                        course_id,
                                        assignment_id
                        ) total_submissions
                        ON (
                            enrollee.uid = total_submissions.uid
                            AND
                            enrollee.course_id = total_submissions.course_id
                            AND
                            total_submissions.assignment_id = %(assignment_id)s
                        )
                        LEFT OUTER JOIN (
                            SELECT      uid,
                                        course_id,
                                        assignment_id,
                                        submission_id
                            FROM        core.submission
                            WHERE       state = 'accepted'
                                        AND
                                        assignment_id = %(assignment_id)s
                        ) accepted
                        ON (
                            enrollee.uid = accepted.uid
                            AND
                            enrollee.course_id = accepted.course_id
                        )
            WHERE       enrollee.course_id = %(course_id)s
        """
        self.cursor.execute(SQL, kwargs)
        return [dict(zip([k[0] for k in self.cursor.description], row)) for row in self.cursor]


# EOF