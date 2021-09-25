#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Evaluation.py - Data dictionary class for assistant.evaluation
#   2021-09-06  Initial version.
#
#
# NOTES
#
#       This class does not have the standard .db_update() because
#       no direct INSERT/UPDATE/DELETE are allowed on the table.
#       Instead, database functions and procedures are to be used:
#       assistant.evaluation_being(
#           %(assistant_uid)s,
#           %(submission_id)s
#       )
#       assistant.evaluation_accept(
#           %(assistant_uid)s,
#           %(submission_id)s,
#           %(score)s,
#           %(feedback)s
#           %(confidential)s
#       )
#       assistant.evaluation_reject()
#       assistant.evaluation_cancel()
from schooner.db.email  import Template
from schooner.jtd       import JTDSubmission


class Evaluation(dict):

    def __init__(self, cursor, submission_id: int = None):
        self.cursor = cursor
        # Primary key is whatever are the call parameters, minus the first two
        self.pk = [k for k in locals().keys() if k not in ('self', 'cursor')]
        self.pkvals = locals() # to avoid KeyError while being used inside comprehensions
        self.pkvals = [self.pkvals[k] for k in self.pk]
        self.SQL = f"SELECT * FROM assistant.{self.__class__.__name__} WHERE "
        if all(self.pkvals):
            self.SQL += " AND ".join([f"{pk}=%({pk})s" for pk in self.pk])
        else:
            self.SQL += "false"
        if self.cursor.execute(self.SQL, locals()).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in self.cursor.description],
                        self.cursor.fetchone()
                    )
                )
            )
        elif all([v is None for v in self.pkvals]):
            # (all) PKs are None -> Create empty dict
            self.update(
                dict(
                    zip(
                        [key[0] for key in self.cursor.description],
                        [None] * len(self.cursor.description)
                    )
                )
            )
        else:
            raise ValueError(
                f"{self.__class__.__name__} (" +
                ", ".join(f"'{v}'" for v in self.pkvals) +
                ") not found!"
            )




    def __update(self):
        SQL = """
            SELECT      *
            FROM        assistant.evaluation
            WHERE       submission_id = %(submission_id)s
        """
        if self.cursor.execute(SQL, self).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in self.cursor.description],
                        self.cursor.fetchone()
                    )
                )
            )
        else:
            raise Exception(
                "Query to update dictionary content failed to find a row! \n" +
                self.SQL + "\n" + str(self)
            )
        return self




    def begin(self, course_id: str = None, uid: str = None) -> int:
        """Begins evaluation and returns an access token. If argument is not supplied, one is used from the object instance. If that does not exist either, an exception is raised."""
        if course_id:
            self['course_id'] = course_id
        if uid:
            self['uid'] = uid
        if not self['course_id'] or not self['uid']:
            raise ValueError(
                "Assistant assignment ('course_id', 'uid') must have values!\n" +
                f"(course_id: '{self['course_id']}', uid: '{self['uid']}')"
            )
        # Function selects the longest-waiting 'draft' submission and returns an accesscode
        SQL = """
            SELECT      *
            FROM        assistant.evaluation_begin(%(course_id)s, %(uid)s) new_eval
        """
        self['submission_id'], accesstoken = self.cursor.execute(SQL, self).fetchone()
        # Commit and release locks
        self.cursor.connection.commit()
        # update/relaod this dictionary
        self.__update()
        return accesstoken




    def accept(self, score: int, feedback: str, confidential: str):
        """TBA"""
        # Query returns TIMESTAMP spent on evaluation
        SQL = """
            SELECT      assistant.evaluation_close(
                %(uid)s,
                %(submission_id)s,
                %(score)s,
                %(feedback)s,
                %(confidential)s
            )
        """
        elapsed = self.cursor.execute(
            SQL,
            { **self, **locals() }
        ).fetchone()[0]
        self.cursor.connection.commit()
        self.__update()
        # Send reject message
        template        = Template(self.cursor, 'EVALUATION_ACCEPTED')
        data            = JTDSubmission(self.cursor, self['submission_id'])
        template.parse_and_queue(
            data['course_id'],
            data['enrollee_uid'],
            **data
        )
        self.cursor.connection.commit()
        return elapsed




    def reject(self, feedback: str, confidential: str):
        """Writes .feedback and .confidential. Awards zero points and sets the status as 'rejected'. Returns the time elapsed in evaluation."""
        SQL = """
            SELECT assistant.evaluation_reject(
                %(uid)s,
                %(submission_id)s,
                %(feedback)s,
                %(confidential)s
            )
        """
        elapsed = self.cursor.execute(
            SQL,
            { **self, **locals() }
        ).fetchone()[0]
        self.cursor.connection.commit()
        self.__update()
        # Send reject message
        template        = Template(self.cursor, 'EVALUATION_REJECTED')
        data            = JTDSubmission(self.cursor, self['submission_id'])
        template.parse_and_queue(
            data['course_id'],
            data['enrollee_uid'],
            **data
        )
        self.cursor.connection.commit()
        return elapsed




    def cancel(self, commit: bool = True):
        """Removes the assistant.evaluation record (and the associated access token). Clears the dictionary."""
        SQL = "SELECT assistant.evaluation_cancel(%(uid)s, %(submission_id)s)"
        self.cursor.execute(SQL, self)
        if commit:
            self.cursor.connection.commit()




# EOF