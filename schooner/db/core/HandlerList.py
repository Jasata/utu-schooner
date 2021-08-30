#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# HandlerList.py - List of data dictionaries for core.handler
#   2021-08-30  Initial version.
#


class HandlerList(list):
    def __init__(self, cursor):
        SQL = """
            SELECT      *
            FROM        core.handler
        """
        super().__init__(
            [dict(zip([k[0] for k in cursor.description], row)) for row in cursor]
        )


# EOF