#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# CourseList.py - List of data dictionaries for core.course
#   2021-08-30  Initial version.
#

class CourseList(list):

    def __init__(self, cursor, **kwargs):
        self.SQL = """
            SELECT      *
            FROM        core.course
        """
        where = []
        for k, v in kwargs.items():
            if k == 'handler':
                if isinstance(v, str):
                    kwargs[k] = [v]
                where.append(
                    """course_id IN (
                        SELECT      distinct course_id
                        FROM        core.assignment
                        WHERE       handler = ANY(%(handler)s)
                    )
                    """
                )
            else:
                if not isinstance(v, list):
                    kwargs[k] = [v]
                where.append(f" {k} = ANY(%({k})s) ")
        if where:
            self.SQL += f" WHERE {' AND '.join(where)}"
        self.args = kwargs
        if cursor.execute(self.SQL, kwargs).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
            )


    def sort(self, key):
        super().sort(key=lambda k : k[key])



# EOF
