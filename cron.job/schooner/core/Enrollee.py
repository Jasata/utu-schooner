#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Enrollee.py - Data dictionary class for core.enrollee
#   2021-08-27  Initial version.
#

class Enrollee(dict):
    def __init__(self, cursor, course_id: str = None, uid: str = None):
        SQL = """
            SELECT      *
            FROM        core.enrollee
            WHERE       course_id = %(course_id)s
                        AND
                        uid = %(uid)s
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
        elif course_id is None and uid is None:
            # Create empty dict
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        [None] * len(cursor.description)
                    )
                )
            )
        else:
            raise ValueError(f"Enrollee ('{course_id}', '{uid}') not found!")


# EOF
