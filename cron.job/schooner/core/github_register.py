#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# github_register.py - Function to register GitHub account
#   2021-08-27  Initial version.
#
#
# Caller is assumed to have matched the registration submission with
# a corresponding invitation before calling this function.
#
from ..email    import Template
from .          import Submission
from .          import Enrollee
from .          import Course

def github_register(cursor, submission_id: int, repository: str) -> None:
    cursor.execute(
        "CALL core.register_github(%(submission_id)s, %(repository)s)",
        locals()
    )
    #
    # Send registration message
    #
    template    = Template(cursor, 'HUBREG')
    submission  = Submission(cursor, submission_id)
    enrollee    = Enrollee(cursor, submission['uid'])
    course      = Course(cursor, submission['course_id'])
    template.parse_and_send(
        submission['course_id'],
        submission['uid'],
        { 'course' : course, 'enrollee' : enrollee }
    )



# EOF
