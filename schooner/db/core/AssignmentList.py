#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# AssignmentList.py - List of data dictionaries for core.assignment
#   2021-08-30  Initial version.
#
from datetime import timedelta
from datetime import datetime
from datetime import date

class AssignmentList(list):

    def __init__(self, cursor, **kwargs):
        self.SQL = """
            SELECT      *
            FROM        core.assignment
        """
        where = []
        for k, v in kwargs.items():
            if not isinstance(v, list):
                kwargs[k] = [v]
            if k == 'active_course':
                kwargs.pop(k)
                where.append(
                    """
                    course_id IN (
                        SELECT      course_id
                        FROM        core.course
                        WHERE       opens > CURRENT_TIMESTAMP
                                    AND
                                    (
                                        closes IS NULL
                                        OR
                                        closes < CURRENT_TIMESTAMP
                                    )
                    )
                    """
                )
            else:
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

    def filter_deadlines(self):
        filtered_list = []
        for assignment in list(filter(lambda assignment: assignment['deadline'] < date.today(), self)):
            if date.today() - assignment['deadline'] == timedelta(1):
                filtered_list.append(assignment)
            elif assignment['latepenalty'] == None:
                continue
            elif (date.today() - assignment['deadline']).days * assignment['latepenalty'] < 100:
                filtered_list.append(assignment)
        return filtered_list



# EOF