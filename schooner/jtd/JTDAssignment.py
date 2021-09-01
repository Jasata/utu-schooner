#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# JTDSubmission.py - Jinja Template Data for a submission
#   2021-08-28  Initial version.
#

class JTDSubmission(dict):
    def __init__(self, cursor, assignmnet_id: int):
        SQL = """
            SELECT      *
            FROM        email.jtd_assignment_rec(%(assignmnet_id)s)
        """
        if cursor.execute(SQL, locals()).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )
        else:
            raise ValueError(f"Assignment #{assignmnet_id} not found!")




# EOF