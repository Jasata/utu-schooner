#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# LogList.py - List of data dictionaries for system.log
#   2021-08-30  Initial version.
#

class LogList(list):
    def __init__(self, cursor, **kwargs):
        self.SQL = """
            SELECT      *
            FROM        system.log
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
            super().__init__([
                dict(
                    zip(
                        [k[0] for k in cursor.description],
                        row
                    )
                ) for row in cursor
            ])




    def sort(self, key, desc: bool = False):
        super().sort(key=lambda k : k[key], reverse = desc)




# EOF