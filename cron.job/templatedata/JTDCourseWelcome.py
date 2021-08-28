#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# JTDCourseWelcome.py - Jinja Template Data for a course welcome message
#   2021-08-28  Initial version.
#

class JTDCourseWelcome(dict):
    def __init__(self, cursor, course_id: int):
        SQL = """
            SELECT      *
            FROM        email.jtd_course_welcome_rec(%(course_id)s)
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
            raise ValueError(f"Course '{course_id}'' not found!")


# EOF
