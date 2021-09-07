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

from schooner.db.email  import Template
from schooner.jtd       import JTDSubmission
from schooner.jtd       import JTDAssignment
from datetime           import timedelta
from datetime           import datetime
from datetime           import date

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

    
    @staticmethod
    def register_as_submission(cursor, student:dict, assignment:dict) -> None:
        sql = """
        INSERT INTO core.submission (
            assignment_id, 
            course_id, 
            uid,
            content,
            submitted, 
            state
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING submission_id
        """
        submission_date = datetime.combine(date.today() - timedelta(1), datetime.max.time())
        cursor.execute(
            sql,
            (
                assignment['assignment_id'],
                assignment['course_id'],
                student['uid'],
                'submission content',
                submission_date,
                'draft'
            )
        )
        submission_id   = cursor.fetchone()[0]
        template        = Template(cursor, 'HUBBOT_SUCCESS')
        data            = JTDSubmission(cursor, submission_id)
        template.parse_and_queue(
            data['course_id'],
            data['enrollee_uid'],
            **data
        )

        
    @staticmethod
    def send_retrieval_failure_mail(cursor, assignment:dict, uid:str, explain:str) -> None:
        template    = Template(cursor, 'HUBBOT_FAIL')
        data = JTDAssignment(
                    cursor, 
                    assignment['course_id'], 
                    assignment['assignment_id'], 
                    uid
                )
                
        template.parse_and_queue(
            assignment['course_id'],
            uid,
            **{**data, 'explain': explain}
        )


# EOF
