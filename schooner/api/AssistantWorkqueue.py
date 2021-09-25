#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# AssistantWorkqueue.py - Data object for assistant workqueue
#   2021-09-04  Initial version.
#   2021-09-25  Support for NULL and NOT NULL column criterion.
#
#


class AssistantWorkqueue(list):
    """List of dictionaries. All unevaluated HUBBOT type submissions for course(s) in which the assistant uid is registered as an active assistant."""

    def __init__(self, cursor, uid:str, **kwargs):
        """Queries all unevaluated HUBBOT type submissions from course(s) in which the specified uid (assistant) is registered in, and is in active status. kwargs may specify column (key) = values that will be used to filter the results. Value may be a single value or list of values."""
        self.SQL = """
            SELECT      *
            FROM        assistant.workqueue(%(uid)s)
        """
        where = []
        for k, v in kwargs.items():
            if v is None or (isinstance(v, bool) and v is False):
                where.append(f" {k} IS NULL")
            elif (isinstance(v, bool) and v is True):
                where.append(f" {k} IS NOT NULL")
            else:
                if not isinstance(v, list):
                    kwargs[k] = [v]
                where.append(f" {k} = ANY(%({k})s) ")
        # Crete WHERE clause
        if where:
            self.SQL += f" WHERE {' AND '.join(where)}"
        kwargs['uid'] = uid
        self.args = kwargs
        if cursor.execute(self.SQL, kwargs).rowcount:
            super().__init__(
                [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
            )




    def sort(self, key, desc: bool = False):
        super().sort(key=lambda k : k[key], reverse = desc)
        return self




# EOF