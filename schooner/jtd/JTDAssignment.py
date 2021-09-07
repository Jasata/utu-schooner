#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# JTDAssignment.py - Jinja Template Data for an assignment
#   2021-08-28  Initial version.
#

class JTDAssignment(dict):

    def __init__(self, cursor, course_id: str, assignment_id: int, uid: str):
        SQL = """
            SELECT      *
            FROM        email.jtd_assignment_rec(
                %(course_id)s,
                %(assignment_id)s,
                %(uid)s
            )
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
            raise ValueError(f"Assignment ('{course_id}', '{assignment_id}', '{uid}') not found!")




# EOF