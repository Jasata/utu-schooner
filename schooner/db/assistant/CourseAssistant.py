#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# CourseAssistant.py - Data dictionary class for assistant.assistant
#   2021-09-06  Initial version.
#
#
# Consider this more "proper" data object than "Assistant"


class CourseAssistant(dict):

    def __init__(self, cursor, course_id: str, uid: str):
        self.cursor = cursor
        self['course_id'] = course_id
        self['uid'] = uid
        self.__update_self()

    def __update_self(self):
        self.SQL = """
            SELECT      assistant.uid,
                        assistant.name,
                        assistant.status,
                        course.course_id,
                        course.name AS course_name,
                        course.code AS course_code,
                        course.opens AS course_opens,
                        course.closes AS course_closes,
                        evaluation.submission_id AS open_submission_id,
                        evaluation.started AS open_datetime
            FROM        assistant.assistant
                        INNER JOIN core.course
                        ON (assistant.course_id = course.course_id)
                        LEFT OUTER JOIN (
                            SELECT      *
                            FROM        assistant.evaluation
                            WHERE       ended IS NULL
                        ) evaluation
                        ON (
                            assistant.uid = evaluation.uid
                            AND
                            assistant.course_id = evaluation.course_id
                        )
            WHERE       assistant.uid = %(uid)s
                        AND
                        assistant.course_id = %(course_id)s
        """
        if not self.cursor.execute(self.SQL, self).rowcount:
            raise Exception(
                f"Assistant '{self['uid']}' registration for course '{self['course_id']}' not found!"
            )
        self.update(
                dict(
                    zip(
                        [key[0] for key in self.cursor.description],
                        self.cursor.fetchone()
                    )
                )
            )




    def db_update(self, commit: bool = True) -> None:
        SQL = """
            UPDATE  assistant.assistant
            SET     name = %(name)s,
                    status = %(status)s
            WHERE   course_id = %(course_id)s
                    AND
                    uid = %(uid)s
        """
        self.cursor.excute(SQL, self)
        if commit:
            self.cursor.connection.commit()




# EOF