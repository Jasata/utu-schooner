#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# CourseList.py - List of data dictionaries for core.course
#   2021-08-30  Initial version.
#   2021-08-31  Supports keyword 'uid' and returns enrolled course.
#

class CourseList(list):

    def __init__(self, cursor, **kwargs):
        self.SQL = """
            SELECT      *
            FROM        core.course
        """
        where = []
        for k, v in kwargs.items():
            if not isinstance(v, list):
                kwargs[k] = [v]
            if k == 'handler':
                where.append(
                    """course_id IN (
                        SELECT      distinct course_id
                        FROM        core.assignment
                        WHERE       handler = ANY(%(handler)s)
                    )
                    """
                )
            elif k == 'ongoing':
                where.append(
                    """
                    opens < CURRENT_TIMESTAMP
                    AND
                    (
                        closes IS NULL
                        OR
                        closes > CURRENT_TIMESTAMP
                    )
                    """
                )
            elif k == 'uid':
                where.append(
                    """course_id IN (
                        SELECT      course_id
                        FROM        core.enrollee
                        WHERE       uid = ANY(%(uid)s)
                    )
                    """
                )
            else:
                where.append(f" {k} = ANY(%({k})s) ")
        if where:
            self.SQL += f" WHERE {' AND '.join(where)}"
        # Remove "dud" keys
        kwargs.pop('ongoing', None)
        self.args = kwargs
        if cursor.execute(self.SQL, kwargs).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
            )


    def sort(self, key):
        super().sort(key=lambda k : k[key])



# EOF
