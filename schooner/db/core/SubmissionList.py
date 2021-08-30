#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# SubmissionList.py - List of data dictionaries for core.submission
#   2021-08-30  Initial version.
#


class SubmissionList(list):

    def __init__(self, cursor, **kwargs):
        self.SQL = """
            SELECT      *
            FROM        core.submission
        """
        where = []
        for k, v in kwargs.items():
            if isinstance(v, list):
                where.append(f" {k} = ANY(%({k})s) ")
            else:
                where.append(f" {k} = %({k})s ")
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
