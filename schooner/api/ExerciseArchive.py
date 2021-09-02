#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Schooner - Course Management System
# University of Turku / Faculty of Technilogy / Department of Computing
# (c) 2021, Jani Tammi <jasata@utu.fi>
#
# ExerciseArchive.py - Class to retrieve and archive exercise for download.
#   2021-09-02  Initial version.
#
import os
from schooner.db.core       import Submission
from schooner.db.system     import Config


class ExerciseArchive:

    def __init__(self, cursor, submission_id: int):
        self.directory = dir = Config(cursor).exercise_directory
        submission = Submission(cursor, submission_id)
        path = os.path.join(
            self.directory,
            submission['course_id'],
            submission['uid'],
            submission['assignment_id']
        )
        raise ValueError(f"{path}")




# EOF