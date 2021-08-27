#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Assignment.py - Data dictionary class for core.course
#   2021-08-27  Initial version.
#

class Assignment(dict):
    def __init__(self, cursor, course_id: str = None, assignment_id: str = None):
        SQL = """
            SELECT      *
            FROM        core.assignment
            WHERE       course_id = %(course_id)s
                        AND
                        assignment_id = %(assignment_id)s
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
        elif course_id is None and assignment_id is None:
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
            raise ValueError(f"Assignment ('{course_id}', '{assignment_id}') not found!")


# EOF
