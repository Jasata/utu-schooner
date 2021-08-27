#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Submission.py - Data dictionary class for core.submission
#   2021-08-27  Initial version.
#

class Submission(dict):
    def __init__(self, cursor, submission_id: int = None):
        SQL = """
            SELECT      *
            FROM        core.submission
            WHERE       submission_id = %(submission_id)s
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
        elif submission_id is None:
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
            raise ValueError(f"Submission #{submission_id} not found!")


# EOF
