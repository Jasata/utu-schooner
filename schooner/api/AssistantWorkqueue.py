#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# AssistantWorkqueue.py - Data object for assistant workqueue
#   2021-09-04  Initial version.
#
#


class AssistantWorkqueue(list):

    def __init__(self, cursor, uid:str, **kwargs):
        self.SQL = """
            SELECT      *
            FROM        assistant.workqueue(%(uid)s)
        """
        where = []
        for k, v in kwargs.items():
            if not isinstance(v, list):
                kwargs[k] = [v]
            where.append(f" {k} = ANY(%({k})s) ")
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