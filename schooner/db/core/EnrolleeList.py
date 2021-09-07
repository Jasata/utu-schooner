#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# EnrolleeList.py - List of data dictionaries for core.enrollee
#   2021-08-30  Initial version.
#


class EnrolleeList(list):

    def __init__(self, cursor, **kwargs):
        self.SQL = """
            SELECT      *
            FROM        core.enrollee
        """
        where = []
        for k, v in kwargs.items():
            if not isinstance(v, list):
                kwargs[k] = [v]
            if k == 'has_github_account':
                where.append(
                    """
                    github_account IS NOT NULL
                    """
                )
            else:
                where.append(f" {k} = ANY(%({k})s) ")
        if where:
            self.SQL += f" WHERE {' AND '.join(where)}"
        # Remove "dud" keys
        kwargs.pop('has_github_account', None)
        self.args = kwargs
        if cursor.execute(self.SQL, kwargs).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
            )




    def sort(self, key, desc: bool = False):
        super().sort(key=lambda k : k[key], reverse = desc)





# EOF
