#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# AssistantList.py - List of assistant assignments on course.
#   2021-09-04  Initial version.
#   2021-09-26  Added student and draft submission counts.
#
# Combines assistant and course data. At the time of writing, used only by the
# assistant index view (listing the courses in which the authenticated
# assistant is assigned into).
#


class AssistantList(list):

    def __init__(self, cursor, **kwargs):
        self.SQL = """
            SELECT      assistant.course_id,
                        assistant.uid AS assistant_uid,
                        assistant.name AS assistant_name,
                        assistant.created AS assistant_created,
                        assistant.status AS assistant_status,
                        course.code AS course_code,
                        course.name AS course_name,
                        course.email AS course_email,
                        course.opens AS course_opens,
                        course.closes As course_closes,
                        COUNT(enrollee.ecid) AS n_active_enrollees,
                        submission.n_draft_submissions
            FROM        assistant.assistant
                        INNER JOIN core.course
                        ON (assistant.course_id = course.course_id)
                        LEFT OUTER JOIN (
                            SELECT      enrollee.course_id AS ecid
                            FROM        core.enrollee
                            WHERE       enrollee.status = 'active'
                        ) enrollee
                        ON (assistant.course_id = enrollee.ecid)
                        LEFT OUTER JOIN (
                            SELECT      assignment.course_id AS cid,
                                        COUNT(submission.submission_id) AS n_draft_submissions
                            FROM        core.assignment
                                        LEFT OUTER JOIN core.submission
                                        ON (
                                            assignment.course_id = submission.course_id
                                            AND
                                            assignment.assignment_id = submission.assignment_id
                                            AND
                                            submission.state = 'draft'
                                            AND
                                            assignment.handler = 'HUBBOT'
                                        )
                            GROUP BY    assignment.course_id
                        ) submission
                        ON (assistant.course_id = submission.cid)
        """
        where = []
        for k, v in kwargs.items():
            if not isinstance(v, list):
                kwargs[k] = [v]
            if k == 'ongoing':
                where.append(
                    """course.opens < CURRENT_TIMESTAMP
                        AND
                        (
                            course.closes IS NULL
                            OR
                            course.closes > CURRENT_TIMESTAMP
                    """
                )
            elif k == 'course_id':
                # Ambigious unless...
                where.append(" course.course_id = ANY(%(course_id)s) ")
            else:
                where.append(f" {k} = ANY(%({k})s) ")
        if where:
            self.SQL += f" WHERE {' AND '.join(where)}"
        self.SQL += """
            GROUP BY    assistant.course_id,
                        assistant.uid,
                        assistant.name,
                        assistant.created,
                        assistant.status,
                        course.code,
                        course.name,
                        course.email,
                        course.opens,
                        course.closes,
                        submission.n_draft_submissions
        """
        # Remove "dud" keys
        kwargs.pop('ongoing', None)
        self.args = kwargs
        if cursor.execute(self.SQL, kwargs).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
            )




    def sort(self, key, desc: bool = False):
        super().sort(key=lambda k : k[key], reverse = desc)




# EOF