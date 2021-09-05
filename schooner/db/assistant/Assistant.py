#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Assistant.py - Data dictionary class for assistant.assistant
#   2021-09-04  Initial version.
#
#
# NOTE
#       This is not "proper" assistant dataobject, but rather a
#       "course assistant" object because same uid can appear any number of
#       times in the assistant -table (once per course assigned to as an
#       assistant).
#
#       This has significance for (currently only) identifying attribute,
#       the ".name", which had redundant and possibly differing values for
#       each course assingment.
#
#       This is accepted as long as there are no other identifying and
#       redundant attributes. If there becomes a need to have more such,
#       this datastructure should be modified into "assistant" and
#       "course_assistant" (the current assistant.assistant table).
#
from typing import Type




class Assistant(dict):

    def __init__(self, cursor, course_id: str = None, uid: str = None):
        self.cursor = cursor
        # Primary key is whatever are the call parameters, minus the first two
        self.pk = [k for k in locals().keys() if k not in ('self', 'cursor')]
        self.pkvals = locals() # to avoid KeyError while being used inside comprehensions
        self.pkvals = [self.pkvals[k] for k in self.pk]
        SQL = f"SELECT * FROM assistant.{self.__class__.__name__} WHERE "
        if all(self.pkvals):
            SQL += " AND ".join([f"{pk}=%({pk})s" for pk in self.pk])
        else:
            SQL += "false"
        if cursor.execute(SQL, locals()).rowcount:
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        cursor.fetchone()
                    )
                )
            )
        elif all([v is None for v in self.pkvals]):
            # (all) PKs are None -> Create empty dict
            self.update(
                dict(
                    zip(
                        [key[0] for key in cursor.description],
                        [None] * len(cursor.description)
                    )
                )
            )
        else:
            raise ValueError(
                f"{self.__class__.__name__} (" +
                ", ".join(f"'{v}'" for v in self.pkvals) +
                ") not found!"
            )




    def db_update(self, commit: bool = True) -> None:
        """Update database table to match. (Will not INSERT)."""
        issues = []
        for k in self.pk:
            if not self[k]:
                issues.append(k)
        if issues:
            raise ValueError(
                f"Primary key value(s) ({', '.join(issues)}) have NULL values!"
            )
        SQL  = f"UPDATE assistant.{self.__class__.__name__} SET "
        SQL += ", ".join([f"{k}=%({k})s" for k in self.keys() if k not in self.pk])
        SQL += " WHERE "
        SQL += " AND ".join([f"{pk}=%({pk})s" for pk in self.pk])
        if not self.cursor.execute(SQL, self).rowcount:
            raise Exception(
                f"Unable to UPDATE {self.__class__.__name__} (" +
                ", ".join(f"'{self[k]}'" for k in self.pk) + ")!"
            )
        if commit:
            self.cursor.connection.commit()




    def currently_evaluating(self):
        """Return submission_id of the evaluation in progress, or None."""
        SQL = """
            SELECT      submission_id
            FROM        assistant.evaluation
            WHERE       uid = %(uid)s
                        AND
                        ended IS NULL
        """
        if self.cursor.execute(SQL, self).rowcount:
            return self.cursor.fetchone()[0]
        else:
            return None




    @staticmethod
    def is_assistant(cursor, uid: str) -> bool:
        """Does the uid have any attachments into courses as an assistant?"""
        SQL = """
            SELECT      course_id
            FROM        assistant.assistant
            WHERE       uid = %(uid)s
        """
        return bool(cursor.execute(SQL, locals()).rowcount)




    @staticmethod
    def in_course(cursor, course_id: str, uid: str) -> bool:
        """True/False if uid is an assistant in the specified course."""
        SQL = """
            SELECT      course_id
            FROM        assistant.assistant
            WHERE       uid = %(uid)s
                        AND
                        course_id = %(course_id)s
        """
        return bool(cursor.execute(SQL, locals()).rowcount)




    @staticmethod
    def get_name(cursor, uid: str) -> str:
        """Returns the .name field from latest course assistant assignment."""
        SQL = """
            SELECT      name
            FROM        assistant.assistant
            WHERE       uid = %(uid)s
            ORDER BY    created DESC
            LIMIT 1
        """
        if not cursor.execute(SQL, locals()).rowcount:
            raise ValueError(
                f"No assistant attachments found for user id '{uid}'!"
            )
        return cursor.fetchone()[0]




    @classmethod
    def create(cls, cursor, course_id: str, uid: str, name: str):
        """Returns a class instance (object) of the newly created record. NOTE: Does not commit!"""
        SQL = """
            INSERT INTO assistant.assistant
            (
                course_id,
                uid,
                name
            )
            VALUES
            (
                %(course_id)s,
                %(uid)s,
                %(name)s
            )
        """
        if not cursor.execute(SQL, locals()).rowcount:
            raise Exception(
                f"Unable to create Assistant('{course_id}', '{uid}', '{name}')!"
            )
        return cls(cursor, course_id, uid)




# EOF
