#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# Course.py - Data dictionary class for core.course
#   2021-08-27  Initial version.
#   2021-09-03  Updated for a flexible version with .db_update().
#

class Course(dict):
    def __init__(self, cursor, course_id: str = None):
        self.cursor = cursor
        # Primary key is whatever are the call parameters, minus the first two
        self.pk = [k for k in locals().keys() if k not in ('self', 'cursor')]
        self.pkvals = locals() # to avoid KeyError while being used inside comprehensions
        self.pkvals = [self.pkvals[k] for k in self.pk]
        SQL = f"SELECT * FROM core.{self.__class__.__name__} WHERE "
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
        SQL  = f"UPDATE core.{self.__class__.__name__} SET "
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



# EOF
